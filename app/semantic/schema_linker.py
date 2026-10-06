"""Schema linking : retrouver les colonnes/métriques pertinentes pour une question.

Deux embedders :
- TfidfEmbedder  : fallback léger (sklearn), utilisé si SOVEREIGN_EMBEDDER=tfidf ou si
                   sentence-transformers n'est pas disponible.
- BgeM3Embedder  : BGE-M3 via sentence-transformers, chargement lazy.

Qdrant in-memory pour le stockage des vecteurs.
"""
from __future__ import annotations

import os
from typing import Protocol

from app.semantic.model import JoinInfo, MetricInfo, SemanticModel, TableInfo


# ── Protocole Embedder ────────────────────────────────────────────────────────

class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


# ── TF-IDF fallback ───────────────────────────────────────────────────────────

class TfidfEmbedder:
    """Embedder léger basé sur TF-IDF cosine similarity. Pas de téléchargement réseau."""

    def __init__(self) -> None:
        from sklearn.feature_extraction.text import TfidfVectorizer
        self._vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4))
        self._fitted = False
        self._corpus: list[str] = []

    def fit(self, corpus: list[str]) -> None:
        self._corpus = corpus
        self._vec.fit(corpus)
        self._fitted = True

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not self._fitted:
            self._vec.fit(texts)
            self._fitted = True
        return self._vec.transform(texts).toarray().tolist()


# ── BGE-M3 Embedder ───────────────────────────────────────────────────────────

class BgeM3Embedder:
    """Embedder BGE-M3 via sentence-transformers (chargement lazy)."""

    _MODEL_NAME = "BAAI/bge-m3"

    def __init__(self) -> None:
        self._model = None

    def _load(self) -> None:
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._MODEL_NAME)

    def embed(self, texts: list[str]) -> list[list[float]]:
        self._load()
        return self._model.encode(texts, normalize_embeddings=True).tolist()  # type: ignore[union-attr]


def default_embedder() -> Embedder:
    """Retourne l'embedder selon SOVEREIGN_EMBEDDER (bge-m3 | tfidf)."""
    choice = os.environ.get("SOVEREIGN_EMBEDDER", "bge-m3").lower()
    if choice == "tfidf":
        return TfidfEmbedder()
    try:
        import sentence_transformers  # noqa: F401
        return BgeM3Embedder()
    except ImportError:
        return TfidfEmbedder()


# ── SchemaLinker ──────────────────────────────────────────────────────────────

_COLL = "schema_items"


class SchemaLinker:
    """Indexe les colonnes et métriques sémantiques ; retrouve les plus pertinentes."""

    def __init__(self, model: SemanticModel, embedder: Embedder, top_k: int = 8) -> None:
        self._model = model
        self._embedder = embedder
        self._top_k = top_k
        self._client = None
        self._items: list[dict] = []
        self._indexed = False

    def _qdrant(self):
        if self._client is None:
            from qdrant_client import QdrantClient
            self._client = QdrantClient(":memory:")
        return self._client

    def index(self) -> None:
        """Construit l'index vectoriel à partir du modèle sémantique."""
        from qdrant_client.models import Distance, PointStruct, VectorParams

        items: list[dict] = []
        texts: list[str] = []

        for table in self._model.tables:
            for col in table.columns:
                text = f"{table.name} {col.name} {col.description} {col.type}"
                items.append({"table": table.name, "col": col.name, "metric": None})
                texts.append(text)

        for metric in self._model.metrics:
            aliases = " ".join(metric.aliases)
            text = f"{metric.name} {aliases} {metric.description} {metric.sql}"
            items.append({"table": None, "col": None, "metric": metric.name})
            texts.append(text)

        if not texts:
            self._items = []
            return

        # Fit TfidfEmbedder on full corpus if needed
        if isinstance(self._embedder, TfidfEmbedder):
            self._embedder.fit(texts)

        vectors = self._embedder.embed(texts)
        dim = len(vectors[0])

        client = self._qdrant()
        if client.collection_exists(_COLL):
            client.delete_collection(_COLL)
        client.create_collection(
            _COLL,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )
        client.upsert(
            _COLL,
            points=[
                PointStruct(id=i, vector=v, payload=items[i])
                for i, v in enumerate(vectors)
            ],
        )
        self._items = items
        self._indexed = True

    def get_relevant_context(self, question: str) -> str:
        """Retrouve les colonnes/métriques pertinentes et retourne un texte de contexte."""
        if not self._indexed:
            self.index()

        if not self._items:
            return ""

        q_vec = self._embedder.embed([question])[0]
        result = self._qdrant().query_points(_COLL, query=q_vec, limit=self._top_k)
        hits = result.points

        hit_tables: set[str] = set()
        hit_cols: dict[str, list[str]] = {}  # table → [col, ...]
        hit_metrics: list[MetricInfo] = []

        for h in hits:
            p = h.payload
            if p.get("metric"):
                m = next((x for x in self._model.metrics if x.name == p["metric"]), None)
                if m and m not in hit_metrics:
                    hit_metrics.append(m)
                    hit_tables.update(m.tables)
            elif p.get("table"):
                t = p["table"]
                hit_tables.add(t)
                hit_cols.setdefault(t, []).append(p["col"])

        # Add tables referenced by metrics
        for m in hit_metrics:
            for t in m.tables:
                if t not in hit_cols:
                    hit_cols[t] = []

        # Determine needed joins
        needed_joins: list[JoinInfo] = []
        tables_needed = set(hit_tables)
        for j in self._model.joins:
            if j.from_table in tables_needed and j.to_table in tables_needed:
                needed_joins.append(j)

        parts: list[str] = []

        if hit_cols:
            parts.append("Tables et colonnes pertinentes :")
            for table_info in self._model.tables:
                if table_info.name not in hit_cols:
                    continue
                selected_cols = hit_cols[table_info.name]
                if selected_cols:
                    col_parts = []
                    for col in table_info.columns:
                        if col.name in selected_cols:
                            col_parts.append(f"{col.name} ({col.description})" if col.description else col.name)
                    parts.append(f"  {table_info.name} : {', '.join(col_parts)}")
                else:
                    parts.append(f"  {table_info.name} (toutes colonnes)")

        if hit_metrics:
            parts.append("Métriques disponibles :")
            for m in hit_metrics:
                parts.append(f"  {m.name} = {m.sql}")

        if needed_joins:
            parts.append("Jointures disponibles :")
            for j in needed_joins:
                parts.append(f"  {j.from_table} {j.type} JOIN {j.to_table} ON {j.on}")

        if self._model.rules:
            parts.append("Règles :")
            for r in self._model.rules:
                parts.append(f"  - {r}")

        return "\n".join(parts)

"""Few-shot retrieval: inject validated examples into the SQL generation prompt."""
from __future__ import annotations

import math
from dataclasses import dataclass

from app.feedback import FeedbackEntry
from app.semantic.schema_linker import TfidfEmbedder


@dataclass
class FewShotExample:
    question: str
    sql: str
    similarity: float


class FewShotRetriever:
    """Retrieves top-k validated (👍) examples most similar to a given question."""

    def __init__(self, embedder=None, top_k: int = 3) -> None:
        self._embedder: TfidfEmbedder = embedder or TfidfEmbedder()
        self._top_k = top_k
        self._good_entries: list[FeedbackEntry] = []
        self._vectors: list[list[float]] = []
        self._fitted = False

    def fit(self, entries: list[FeedbackEntry]) -> None:
        """Index only 'good' entries. 'bad' entries are ignored."""
        good = [e for e in entries if e.rating == "good"]
        if not good:
            self._good_entries = []
            self._vectors = []
            self._fitted = False
            return
        self._good_entries = good
        texts = [e.question for e in good]
        if hasattr(self._embedder, "fit"):
            self._embedder.fit(texts)
        self._vectors = self._embedder.embed(texts)
        self._fitted = True

    def retrieve(self, question: str) -> list[FewShotExample]:
        """Return top_k examples sorted by descending similarity."""
        if not self._fitted or not self._good_entries:
            return []
        q_vec = self._embedder.embed([question])[0]
        sims = _cosine_similarities(q_vec, self._vectors)
        top_indices = sorted(range(len(sims)), key=lambda i: sims[i], reverse=True)[: self._top_k]
        return [
            FewShotExample(
                question=self._good_entries[i].question,
                sql=self._good_entries[i].sql,
                similarity=round(sims[i], 6),
            )
            for i in top_indices
        ]


def _cosine_similarities(query: list[float], corpus: list[list[float]]) -> list[float]:
    q_norm = math.sqrt(sum(x * x for x in query))
    results = []
    for vec in corpus:
        v_norm = math.sqrt(sum(x * x for x in vec))
        if q_norm == 0.0 or v_norm == 0.0:
            results.append(0.0)
        else:
            dot = sum(a * b for a, b in zip(query, vec))
            results.append(dot / (q_norm * v_norm))
    return results


def format_few_shot(examples: list[FewShotExample]) -> str:
    """Format examples for injection into the SQL generation prompt."""
    if not examples:
        return ""
    lines = ["Exemples validés :"]
    for ex in examples:
        lines.append(f"Q: {ex.question}")
        lines.append(f"SQL: {ex.sql}")
        lines.append("")
    return "\n".join(lines).rstrip()

"""Tests d'intégration pipeline + SchemaLinker (FakeLLM, aucun Ollama)."""
import os

import pytest

os.environ.setdefault("SOVEREIGN_EMBEDDER", "tfidf")

from app.data.duckdb_store import DataStore
from app.pipeline.graph import build_graph
from app.semantic.model import load_model
from app.semantic.schema_linker import SchemaLinker, TfidfEmbedder


class _FakeLLM:
    """LLM factice qui retourne une requête SQL valide."""

    def __init__(self, sql: str = "SELECT 1 AS ok"):
        self._sql = sql
        self.calls: list[tuple[str, str]] = []

    def complete(self, system: str, prompt: str) -> str:
        self.calls.append((system, prompt))
        if "Réponds" in system:  # SQL system
            return f"```sql\n{self._sql}\n```"
        return "Réponse factice."


@pytest.fixture()
def store_with_data(tmp_path):
    import pandas as pd
    s = DataStore()
    df = pd.DataFrame({"montant_ht": [100.0, 200.0], "region": ["Ontario", "Québec"]})
    s.load_dataframe("ventes_detail", df)
    return s


@pytest.fixture()
def linker():
    m = load_model("semantic/model.yaml")
    emb = TfidfEmbedder()
    lk = SchemaLinker(m, emb, top_k=5)
    lk.index()
    return lk


def test_pipeline_with_linker_invokes_llm(store_with_data, linker):
    llm = _FakeLLM("SELECT SUM(montant_ht) AS ca FROM ventes_detail")
    g = build_graph(llm, store_with_data, linker=linker)
    result = g.invoke({"question": "Quel est le chiffre d'affaires ?", "dry_run": True})
    assert len(llm.calls) > 0


def test_pipeline_with_linker_context_injected(store_with_data, linker):
    """Le prompt reçu par le LLM doit contenir le contexte schema linking."""
    llm = _FakeLLM("SELECT 1")
    g = build_graph(llm, store_with_data, linker=linker)
    g.invoke({"question": "Chiffre d'affaires par région", "dry_run": True})
    # At least one call should have a prompt mentioning relevant context
    prompts = [p for _, p in llm.calls]
    combined = "\n".join(prompts)
    assert "ventes_detail" in combined or "montant_ht" in combined


def test_pipeline_without_linker_uses_semantic_str(store_with_data):
    llm = _FakeLLM("SELECT 1")
    g = build_graph(llm, store_with_data, semantic="Glossaire factice : CA = SUM(montant_ht)")
    g.invoke({"question": "CA total", "dry_run": True})
    prompts = [p for _, p in llm.calls]
    combined = "\n".join(prompts)
    assert "Glossaire factice" in combined


def test_pipeline_linker_overrides_semantic_str(store_with_data, linker):
    llm = _FakeLLM("SELECT 1")
    g = build_graph(llm, store_with_data, semantic="SHOULD_NOT_APPEAR", linker=linker)
    g.invoke({"question": "Nombre de commandes", "dry_run": True})
    prompts = [p for _, p in llm.calls]
    combined = "\n".join(prompts)
    assert "SHOULD_NOT_APPEAR" not in combined

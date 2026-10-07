"""Tests : build_graph retourne confidence + injection doc_store."""
from __future__ import annotations

import pandas as pd

from app.data.duckdb_store import DataStore
from app.pipeline.graph import build_graph
from app.rag.doc_store import DocStore


class FakeLLM:
    def complete(self, system, user):
        if "résultats :" in user.lower():
            return "Le CA est 1000."
        return "SELECT region, SUM(montant) AS ca FROM ventes GROUP BY region"


def _store_with_data():
    store = DataStore()
    store.load_dataframe("ventes", pd.DataFrame({"region": ["ON"], "montant": [1000.0]}))
    return store


def test_pipeline_returns_confidence_field():
    store = _store_with_data()
    graph = build_graph(FakeLLM(), store)
    result = graph.invoke({"question": "CA total ?"})
    assert "confidence" in result
    assert result["confidence"] is not None


def test_pipeline_confidence_score_between_0_and_1():
    store = _store_with_data()
    graph = build_graph(FakeLLM(), store)
    result = graph.invoke({"question": "CA par région ?"})
    conf = result["confidence"]
    assert 0.0 <= conf["score"] <= 1.0
    assert conf["label"] in ("élevée", "moyenne", "faible")


def test_pipeline_confidence_has_explanation():
    store = _store_with_data()
    graph = build_graph(FakeLLM(), store)
    result = graph.invoke({"question": "Nombre de commandes ?"})
    assert isinstance(result["confidence"]["explanation"], str)
    assert len(result["confidence"]["explanation"]) > 0


def test_pipeline_with_doc_store_injects_context():
    from unittest.mock import patch

    store = _store_with_data()
    ds = DocStore()
    # Inject a chunk directly via mock
    with patch("app.rag.doc_store._extract_pdf", return_value=["rapport annuel Ontario ventes"]):
        ds.ingest_bytes(b"pdf_content", "rapport.pdf")

    prompts_seen = []

    class CaptureLLM:
        def complete(self, system, user):
            prompts_seen.append(user)
            if "résultats :" in user.lower():
                return "Le CA est 1000."
            return "SELECT region, SUM(montant) AS ca FROM ventes GROUP BY region"

    graph = build_graph(CaptureLLM(), store, doc_store=ds)
    graph.invoke({"question": "rapport Ontario ?"})
    # The SQL generation prompt should include doc context
    sql_gen_prompts = [p for p in prompts_seen if "résultats" not in p.lower()]
    assert any("rapport" in p.lower() for p in sql_gen_prompts)


def test_pipeline_without_doc_store_backward_compatible():
    store = _store_with_data()
    graph = build_graph(FakeLLM(), store)  # no doc_store
    result = graph.invoke({"question": "CA ?"})
    assert result.get("answer") is not None

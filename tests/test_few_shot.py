"""Tests for app/learning/few_shot.py."""
import os

import pandas as pd
import pytest

os.environ.setdefault("SOVEREIGN_EMBEDDER", "tfidf")

from app.feedback import FeedbackEntry
from app.learning.few_shot import FewShotExample, FewShotRetriever, format_few_shot


def _make_entry(question: str, sql: str, rating: str) -> FeedbackEntry:
    return FeedbackEntry(
        timestamp="2026-10-05T10:00:00+00:00",
        question=question,
        sql=sql,
        rating=rating,
    )


# ── retriever core ────────────────────────────────────────────────────────────


def test_retriever_empty_returns_nothing():
    r = FewShotRetriever()
    r.fit([])
    assert r.retrieve("CA total") == []


def test_retriever_not_fitted_returns_nothing():
    r = FewShotRetriever()
    assert r.retrieve("CA total") == []


def test_retriever_only_uses_good_feedback():
    bad = _make_entry("CA par région", "SELECT region FROM ventes", "bad")
    r = FewShotRetriever()
    r.fit([bad])
    assert r.retrieve("CA par région") == []


def test_retriever_ignores_bad_among_mixed():
    good = _make_entry("CA total", "SELECT SUM(montant_ht) FROM ventes_detail", "good")
    bad = _make_entry("CA région", "SELECT region FROM ventes_detail", "bad")
    r = FewShotRetriever()
    r.fit([good, bad])
    results = r.retrieve("CA total")
    assert len(results) == 1
    assert results[0].question == "CA total"


def test_retriever_returns_at_most_top_k():
    entries = [
        _make_entry(f"Question CA {i}", f"SELECT {i} FROM ventes_detail", "good")
        for i in range(10)
    ]
    r = FewShotRetriever(top_k=3)
    r.fit(entries)
    results = r.retrieve("CA total")
    assert len(results) <= 3


def test_retriever_sorted_by_similarity_descending():
    entries = [
        _make_entry("Chiffre affaires total mensuel", "SELECT SUM(montant_ht) FROM ventes_detail", "good"),
        _make_entry("Nombre de clients actifs", "SELECT COUNT(*) FROM clients WHERE actif=TRUE", "good"),
        _make_entry("CA par region Canada", "SELECT region, SUM(montant_ht) FROM ventes_detail GROUP BY region", "good"),
    ]
    r = FewShotRetriever(top_k=3)
    r.fit(entries)
    results = r.retrieve("chiffre affaires region")
    sims = [ex.similarity for ex in results]
    assert sims == sorted(sims, reverse=True)


def test_retriever_example_has_question_and_sql():
    good = _make_entry("CA total", "SELECT SUM(montant_ht) FROM ventes_detail", "good")
    r = FewShotRetriever(top_k=1)
    r.fit([good])
    results = r.retrieve("chiffre affaires")
    assert len(results) == 1
    ex = results[0]
    assert ex.question == "CA total"
    assert "SUM" in ex.sql
    assert 0.0 <= ex.similarity <= 1.0


# ── format_few_shot ───────────────────────────────────────────────────────────


def test_format_few_shot_empty_returns_empty_string():
    assert format_few_shot([]) == ""


def test_format_few_shot_contains_question_and_sql():
    examples = [
        FewShotExample(question="CA total ?", sql="SELECT SUM(montant_ht) FROM ventes_detail", similarity=0.9),
    ]
    text = format_few_shot(examples)
    assert "Q: CA total ?" in text
    assert "SQL: SELECT SUM(montant_ht) FROM ventes_detail" in text


def test_format_few_shot_has_header():
    examples = [FewShotExample(question="q", sql="SELECT 1", similarity=0.5)]
    text = format_few_shot(examples)
    assert "Exemples validés" in text


def test_format_few_shot_multiple_examples():
    examples = [
        FewShotExample(question=f"Question {i}", sql=f"SELECT {i}", similarity=0.9 - i * 0.1)
        for i in range(3)
    ]
    text = format_few_shot(examples)
    for i in range(3):
        assert f"Question {i}" in text
        assert f"SELECT {i}" in text


# ── pipeline integration ──────────────────────────────────────────────────────


def test_pipeline_with_retriever_injects_examples():
    """build_graph with retriever: the SQL generation prompt must include few-shot examples."""
    from app.data.duckdb_store import DataStore
    from app.pipeline.graph import build_graph

    captured_prompts: list[str] = []

    class CapturingLLM:
        def complete(self, system: str, user: str) -> str:
            captured_prompts.append(user)
            if "expert SQL" in system:
                return "```sql\nSELECT SUM(montant_ht) FROM ventes_detail\n```"
            return "Réponse."

    store = DataStore()
    store.load_dataframe(
        "ventes_detail",
        pd.DataFrame({"montant_ht": [100.0, 200.0]}),
    )

    good = _make_entry("CA total", "SELECT SUM(montant_ht) FROM ventes_detail", "good")
    retriever = FewShotRetriever(top_k=1)
    retriever.fit([good])

    g = build_graph(CapturingLLM(), store, retriever=retriever)
    g.invoke({"question": "chiffre affaires"})

    assert len(captured_prompts) >= 1
    first_sql_prompt = captured_prompts[0]
    assert "Exemples validés" in first_sql_prompt
    assert "CA total" in first_sql_prompt


def test_pipeline_without_retriever_unchanged():
    """build_graph without retriever behaves exactly as before (no few-shot section)."""
    from app.data.duckdb_store import DataStore
    from app.pipeline.graph import build_graph

    captured_prompts: list[str] = []

    class CapturingLLM:
        def complete(self, system: str, user: str) -> str:
            captured_prompts.append(user)
            if "expert SQL" in system:
                return "```sql\nSELECT SUM(montant_ht) FROM ventes_detail\n```"
            return "Réponse."

    store = DataStore()
    store.load_dataframe(
        "ventes_detail",
        pd.DataFrame({"montant_ht": [100.0, 200.0]}),
    )

    g = build_graph(CapturingLLM(), store)
    g.invoke({"question": "chiffre affaires"})

    assert len(captured_prompts) >= 1
    assert "Exemples validés" not in captured_prompts[0]

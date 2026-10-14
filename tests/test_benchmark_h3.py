"""Tests for eval/benchmark_h3.jsonl and eval/run_benchmark_h3.py."""
import json
from pathlib import Path

import pytest

BENCHMARK_FILE = Path("eval/benchmark_h3.jsonl")


def load_all():
    questions = []
    with BENCHMARK_FILE.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                questions.append(json.loads(line))
    return questions


def test_benchmark_file_exists():
    assert BENCHMARK_FILE.exists()


def test_benchmark_has_questions():
    questions = load_all()
    assert len(questions) >= 15


def test_all_questions_have_required_fields():
    for q in load_all():
        assert "id" in q
        assert "lang" in q
        assert "sector" in q
        assert "question" in q
        assert "min_keywords" in q


def test_all_ids_unique():
    ids = [q["id"] for q in load_all()]
    assert len(ids) == len(set(ids))


def test_languages_covered():
    langs = {q["lang"] for q in load_all()}
    assert "fr" in langs
    assert "en" in langs
    assert "ar" in langs


def test_sectors_covered():
    sectors = {q["sector"] for q in load_all()}
    assert "humanitarian" in sectors
    assert "igad_economic" in sectors
    assert "instad_census" in sectors


def test_mock_provider_humanitarian_en():
    from eval.run_benchmark_h3 import mock_provider
    sql = mock_provider("How many beneficiaries are registered?", "humanitarian")
    assert "beneficiaires" in sql.lower() or "SUM" in sql.upper()


def test_mock_provider_distributions():
    from eval.run_benchmark_h3 import mock_provider
    sql = mock_provider("How many distributions were completed?", "humanitarian")
    assert "distributions" in sql.lower()


def test_mock_provider_igad_pib():
    from eval.run_benchmark_h3 import mock_provider
    sql = mock_provider("What is the total GDP of IGAD?", "igad_economic")
    assert "pib" in sql.lower() or "SUM" in sql.upper()


def test_evaluate_sql_pass():
    from eval.run_benchmark_h3 import evaluate_sql
    item = {
        "id": "test-01",
        "lang": "en",
        "sector": "humanitarian",
        "question": "test",
        "min_keywords": ["SUM", "beneficiaires"],
        "expected_table": "beneficiaires",
        "expected_metric": None,
    }
    result = evaluate_sql("SELECT SUM(nb_beneficiaires) FROM beneficiaires", item)
    assert result["passed"] is True
    assert result["missing_keywords"] == []


def test_evaluate_sql_fail_missing_keyword():
    from eval.run_benchmark_h3 import evaluate_sql
    item = {
        "id": "test-02",
        "lang": "en",
        "sector": "humanitarian",
        "question": "test",
        "min_keywords": ["SUM", "beneficiaires"],
        "expected_table": "beneficiaires",
        "expected_metric": None,
    }
    result = evaluate_sql("SELECT * FROM distributions", item)
    assert result["passed"] is False
    assert len(result["missing_keywords"]) > 0


def test_load_questions_filter_lang():
    from eval.run_benchmark_h3 import load_questions
    fr_qs = load_questions(lang="fr")
    assert all(q["lang"] == "fr" for q in fr_qs)
    assert len(fr_qs) >= 3


def test_load_questions_filter_sector():
    from eval.run_benchmark_h3 import load_questions
    hum_qs = load_questions(sector="humanitarian")
    assert all(q["sector"] == "humanitarian" for q in hum_qs)


def test_run_with_mock_provider():
    from eval.run_benchmark_h3 import run_with_provider, mock_provider, load_questions
    questions = load_questions(lang="en", sector="humanitarian")
    results = run_with_provider(mock_provider, questions)
    assert len(results) == len(questions)
    passed = sum(1 for r in results if r.get("passed"))
    assert passed >= len(questions) * 0.6

"""Tests — intégrité du jeu d'évaluation (Sprint 2)."""
import json
import sys
from pathlib import Path

import pytest

EVAL_DIR = Path(__file__).parent.parent / "eval"
DATASET = EVAL_DIR / "dataset_large.jsonl"
sys.path.insert(0, str(EVAL_DIR))


def _load_pairs():
    return [json.loads(l) for l in DATASET.read_text(encoding="utf-8").splitlines() if l.strip()]


def test_dataset_large_exists():
    assert DATASET.exists(), "Lancer eval/gen_pairs.py pour générer dataset_large.jsonl"


def test_dataset_large_has_100_pairs():
    pairs = _load_pairs()
    assert len(pairs) == 100


def test_all_pairs_have_required_keys():
    for i, p in enumerate(_load_pairs()):
        assert "question" in p, f"Paire {i} : clé 'question' manquante"
        assert "gold_sql" in p, f"Paire {i} : clé 'gold_sql' manquante"


def test_gold_sql_are_select():
    for p in _load_pairs():
        sql = p["gold_sql"].strip().upper()
        assert sql.startswith("SELECT") or sql.startswith("WITH"), \
            f"SQL non SELECT/WITH : {p['gold_sql']!r}"


def test_no_duplicate_questions():
    questions = [p["question"] for p in _load_pairs()]
    assert len(questions) == len(set(questions)), "Questions dupliquées dans le dataset"


def test_gen_pairs_idempotent(tmp_path):
    """Appeler gen_pairs.main() deux fois produit le même fichier."""
    import gen_pairs as gp
    out1 = tmp_path / "run1.jsonl"
    out2 = tmp_path / "run2.jsonl"
    orig = gp.OUT
    try:
        gp.OUT = out1
        gp.main()
        gp.OUT = out2
        gp.main()
    finally:
        gp.OUT = orig
    assert out1.read_text() == out2.read_text()

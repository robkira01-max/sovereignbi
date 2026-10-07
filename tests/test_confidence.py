"""Tests du certificat de précision."""
from __future__ import annotations

import pytest

from app.pipeline.confidence import ConfidenceScore, compute_confidence


_SENTINEL = object()

def _state(attempts=1, error=None, rows=_SENTINEL):
    return {"attempts": attempts, "error": error, "rows": [("val",)] if rows is _SENTINEL else rows}


def test_one_attempt_no_error_gives_high_score():
    cs = compute_confidence(_state(attempts=1, rows=[("x",)]))
    assert cs.score >= 0.75
    assert cs.label == "élevée"


def test_three_attempts_gives_lower_score():
    cs_one = compute_confidence(_state(attempts=1, rows=[("x",)]))
    cs_three = compute_confidence(_state(attempts=3, rows=[("x",)]))
    assert cs_three.score < cs_one.score


def test_error_state_gives_low_score():
    cs = compute_confidence({"attempts": 3, "error": "SQL invalide", "rows": []})
    assert cs.score < 0.45
    assert cs.label == "faible"


def test_few_shot_hit_increases_score():
    cs_no_fs = compute_confidence(_state(attempts=1, rows=[("x",)]), few_shot_count=0)
    cs_with_fs = compute_confidence(_state(attempts=1, rows=[("x",)]), few_shot_count=2)
    assert cs_with_fs.score > cs_no_fs.score


def test_no_results_reduces_score():
    cs_with = compute_confidence(_state(attempts=1, rows=[("x",)]))
    cs_empty = compute_confidence(_state(attempts=1, rows=[]))
    assert cs_empty.score < cs_with.score


def test_label_high():
    cs = compute_confidence(_state(attempts=1, rows=[("x",)]), few_shot_count=2)
    assert cs.label == "élevée"


def test_label_medium():
    cs = compute_confidence(_state(attempts=2, rows=[]))
    assert cs.label in ("moyenne", "faible")


def test_label_low():
    cs = compute_confidence({"attempts": 3, "error": "err", "rows": []})
    assert cs.label == "faible"


def test_explanation_is_non_empty_string():
    cs = compute_confidence(_state())
    assert isinstance(cs.explanation, str)
    assert len(cs.explanation) > 0


def test_score_between_0_and_1():
    for attempts in [1, 2, 3]:
        for err in [None, "error"]:
            cs = compute_confidence({"attempts": attempts, "error": err, "rows": []})
            assert 0.0 <= cs.score <= 1.0


def test_factors_present():
    cs = compute_confidence(_state())
    for key in ("attempts", "has_results", "few_shot_hit", "no_error"):
        assert key in cs.factors
        assert 0.0 <= cs.factors[key] <= 1.0


def test_explanation_mentions_attempts():
    cs = compute_confidence(_state(attempts=2))
    assert "2" in cs.explanation or "tentative" in cs.explanation


def test_explanation_mentions_few_shot_when_present():
    cs = compute_confidence(_state(), few_shot_count=3)
    assert "3" in cs.explanation or "exemple" in cs.explanation

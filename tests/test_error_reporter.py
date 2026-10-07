"""Tests for app/learning/error_reporter.py."""
from datetime import datetime, timedelta, timezone

from app.feedback import FeedbackEntry
from app.learning.error_reporter import (
    WeeklyReport,
    analyze_errors,
    format_report_markdown,
)


def _entry(question: str, rating: str, days_ago: float = 0.0) -> FeedbackEntry:
    ts = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return FeedbackEntry(
        timestamp=ts.isoformat(),
        question=question,
        sql="SELECT 1",
        rating=rating,
    )


# ── basic counts ──────────────────────────────────────────────────────────────


def test_report_empty_feedback():
    report = analyze_errors([])
    assert report.total_feedback == 0
    assert report.good_count == 0
    assert report.bad_count == 0
    assert report.satisfaction_rate == 1.0
    assert isinstance(report, WeeklyReport)


def test_report_counts_good():
    entries = [_entry("CA total", "good"), _entry("panier moyen", "good")]
    report = analyze_errors(entries)
    assert report.good_count == 2
    assert report.bad_count == 0
    assert report.total_feedback == 2


def test_report_counts_bad():
    entries = [_entry("marge brute", "bad"), _entry("panier moyen", "good")]
    report = analyze_errors(entries)
    assert report.good_count == 1
    assert report.bad_count == 1
    assert report.total_feedback == 2


def test_satisfaction_rate_all_good():
    entries = [_entry("CA", "good"), _entry("clients", "good")]
    report = analyze_errors(entries)
    assert report.satisfaction_rate == 1.0


def test_satisfaction_rate_all_bad():
    entries = [_entry("marge totale", "bad"), _entry("taux calcul", "bad")]
    report = analyze_errors(entries)
    assert report.satisfaction_rate == 0.0


def test_satisfaction_rate_mixed():
    entries = [_entry("CA", "good"), _entry("marge", "bad"), _entry("taux", "bad")]
    report = analyze_errors(entries)
    assert abs(report.satisfaction_rate - 1 / 3) < 0.01


# ── time filter ───────────────────────────────────────────────────────────────


def test_report_filters_by_days():
    recent = _entry("CA total", "bad", days_ago=1)
    old = _entry("vieille question", "bad", days_ago=30)
    report = analyze_errors([recent, old], days=7)
    assert report.total_feedback == 1
    assert report.bad_count == 1


def test_report_includes_all_within_window():
    entries = [_entry("q", "good", days_ago=i) for i in range(7)]
    report = analyze_errors(entries, days=7)
    assert report.total_feedback == 7


# ── error patterns ────────────────────────────────────────────────────────────


def test_error_patterns_from_repeated_failures():
    entries = [
        _entry("Calcul de la marge brute", "bad"),
        _entry("Marge par catégorie", "bad"),
        _entry("CA total", "good"),
    ]
    report = analyze_errors(entries)
    pattern_texts = [p.pattern for p in report.error_patterns]
    assert any("marge" in t.lower() for t in pattern_texts)


def test_error_patterns_contain_examples():
    entries = [_entry("Calculer marge totale", "bad")]
    report = analyze_errors(entries)
    for p in report.error_patterns:
        assert len(p.examples) >= 1


def test_error_patterns_have_suggested_rule():
    entries = [_entry("taux de retour mensuel", "bad")]
    report = analyze_errors(entries)
    for p in report.error_patterns:
        assert p.suggested_rule


def test_top_failing_questions_max_5():
    entries = [_entry(f"question {i}", "bad") for i in range(10)]
    report = analyze_errors(entries)
    assert len(report.top_failing_questions) <= 5


# ── format_report_markdown ───────────────────────────────────────────────────


def test_format_report_markdown_not_empty():
    report = analyze_errors([_entry("CA", "good")])
    md = format_report_markdown(report)
    assert len(md) > 0


def test_format_report_markdown_contains_header():
    report = analyze_errors([])
    md = format_report_markdown(report)
    assert "# Rapport" in md


def test_format_report_markdown_contains_stats():
    entries = [_entry("CA", "good"), _entry("marge totale", "bad")]
    report = analyze_errors(entries)
    md = format_report_markdown(report)
    assert "2" in md  # total feedback
    assert "Synthèse" in md


def test_format_report_markdown_no_patterns_message():
    report = analyze_errors([])
    md = format_report_markdown(report)
    assert "Aucun pattern" in md

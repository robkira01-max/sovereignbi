"""Tests for app/learning/rule_proposer.py."""
import pytest
import yaml

from app.feedback import FeedbackEntry
from app.learning.error_reporter import analyze_errors
from app.learning.rule_proposer import (
    RuleProposal,
    approve_proposal,
    apply_approved_rules,
    load_proposals,
    propose_rules,
    reject_proposal,
    save_proposal,
)


def _bad_entry(question: str) -> FeedbackEntry:
    from datetime import datetime, timezone

    return FeedbackEntry(
        timestamp=datetime.now(timezone.utc).isoformat(),
        question=question,
        sql="SELECT 1",
        rating="bad",
    )


def _proposal(rule: str = "Règle test") -> RuleProposal:
    return RuleProposal(
        id="abc12345",
        proposed_at="2026-10-05T10:00:00+00:00",
        source="manual",
        rule_text=rule,
        rationale="Test rationale",
        status="pending",
    )


# ── save / load ───────────────────────────────────────────────────────────────


def test_save_load_proposal(tmp_path):
    p = _proposal("Toujours utiliser SUM(montant_ht) pour le CA.")
    path = tmp_path / "proposals.jsonl"
    save_proposal(p, path=path)
    loaded = load_proposals(path=path)
    assert len(loaded) == 1
    assert loaded[0].rule_text == "Toujours utiliser SUM(montant_ht) pour le CA."
    assert loaded[0].status == "pending"


def test_load_proposals_missing_file(tmp_path):
    assert load_proposals(path=tmp_path / "nonexistent.jsonl") == []


def test_load_proposals_by_status_pending(tmp_path):
    path = tmp_path / "proposals.jsonl"
    p1 = _proposal("Règle 1")
    p1.status = "approved"
    p2 = _proposal("Règle 2")
    p2.id = "def67890"
    p2.status = "pending"
    save_proposal(p1, path=path)
    save_proposal(p2, path=path)
    pending = load_proposals(status="pending", path=path)
    assert len(pending) == 1
    assert pending[0].rule_text == "Règle 2"


def test_load_proposals_by_status_approved(tmp_path):
    path = tmp_path / "proposals.jsonl"
    p = _proposal()
    p.status = "approved"
    save_proposal(p, path=path)
    assert len(load_proposals(status="approved", path=path)) == 1
    assert len(load_proposals(status="pending", path=path)) == 0


# ── approve / reject ──────────────────────────────────────────────────────────


def test_approve_proposal(tmp_path):
    path = tmp_path / "proposals.jsonl"
    save_proposal(_proposal(), path=path)
    updated = approve_proposal("abc12345", reviewer="admin", path=path)
    assert updated.status == "approved"
    assert updated.reviewed_by == "admin"
    assert updated.reviewed_at is not None


def test_reject_proposal(tmp_path):
    path = tmp_path / "proposals.jsonl"
    save_proposal(_proposal(), path=path)
    updated = reject_proposal("abc12345", reviewer="admin", path=path)
    assert updated.status == "rejected"


def test_approve_unknown_id_raises(tmp_path):
    path = tmp_path / "proposals.jsonl"
    save_proposal(_proposal(), path=path)
    with pytest.raises(ValueError, match="introuvable"):
        approve_proposal("does-not-exist", reviewer="admin", path=path)


def test_reject_unknown_id_raises(tmp_path):
    path = tmp_path / "proposals.jsonl"
    save_proposal(_proposal(), path=path)
    with pytest.raises(ValueError, match="introuvable"):
        reject_proposal("does-not-exist", reviewer="admin", path=path)


# ── propose_rules ─────────────────────────────────────────────────────────────


def test_propose_rules_from_report():
    entries = [_bad_entry("marge brute des produits"), _bad_entry("marge totale")]
    report = analyze_errors(entries)
    proposals = propose_rules(report)
    assert isinstance(proposals, list)
    assert all(isinstance(p, RuleProposal) for p in proposals)
    assert all(p.status == "pending" for p in proposals)
    assert all(p.source == "error_analysis" for p in proposals)


def test_propose_rules_empty_report():
    from app.learning.error_reporter import WeeklyReport

    report = WeeklyReport(
        generated_at="",
        period_start="",
        period_end="",
        total_feedback=0,
        good_count=0,
        bad_count=0,
        satisfaction_rate=1.0,
        error_patterns=[],
        top_failing_questions=[],
    )
    assert propose_rules(report) == []


# ── apply_approved_rules ─────────────────────────────────────────────────────


def test_apply_approved_adds_rules(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "semantic").mkdir()
    (tmp_path / "data").mkdir()

    model_yaml = {"schema_version": "2", "rules": ["Règle existante."]}
    model_path = tmp_path / "semantic" / "model.yaml"
    model_path.write_text(yaml.dump(model_yaml, allow_unicode=True), encoding="utf-8")

    path = tmp_path / "data" / "proposals.jsonl"
    p = _proposal("Nouvelle règle ajoutée automatiquement.")
    p.status = "approved"
    save_proposal(p, path=path)

    added = apply_approved_rules(
        model_path=model_path,
        proposals_path=path,
        versions_dir=tmp_path / "data" / "semantic_versions",
    )
    assert "Nouvelle règle ajoutée automatiquement." in added

    updated = yaml.safe_load(model_path.read_text(encoding="utf-8"))
    assert "Nouvelle règle ajoutée automatiquement." in updated["rules"]
    assert "Règle existante." in updated["rules"]


def test_apply_creates_snapshot_first(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "semantic").mkdir()
    (tmp_path / "data").mkdir()

    model_path = tmp_path / "semantic" / "model.yaml"
    model_path.write_text(yaml.dump({"schema_version": "2", "rules": []}), encoding="utf-8")

    path = tmp_path / "data" / "proposals.jsonl"
    p = _proposal("Une nouvelle règle.")
    p.status = "approved"
    save_proposal(p, path=path)

    versions_dir = tmp_path / "data" / "semantic_versions"
    apply_approved_rules(
        model_path=model_path,
        proposals_path=path,
        versions_dir=versions_dir,
    )
    snapshots = list(versions_dir.glob("model_*.yaml"))
    assert len(snapshots) >= 1


def test_apply_skips_already_applied(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "semantic").mkdir()
    (tmp_path / "data").mkdir()

    model_path = tmp_path / "semantic" / "model.yaml"
    model_path.write_text(yaml.dump({"schema_version": "2", "rules": []}), encoding="utf-8")

    path = tmp_path / "data" / "proposals.jsonl"
    p = _proposal("Règle déjà appliquée.")
    p.status = "approved"
    p.applied = True
    save_proposal(p, path=path)

    added = apply_approved_rules(
        model_path=model_path,
        proposals_path=path,
        versions_dir=tmp_path / "data" / "semantic_versions",
    )
    assert added == []

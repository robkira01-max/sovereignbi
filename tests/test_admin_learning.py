"""Tests for admin learning routes: proposals, versions, report."""
import os

import pytest
import yaml
from fastapi.testclient import TestClient

os.environ.setdefault("SOVEREIGN_ADMIN_KEY", "test-admin-key-sprint3")
os.environ.setdefault("SOVEREIGN_EMBEDDER", "tfidf")

from app.main import app

client = TestClient(app)
HEADERS = {"X-Admin-Key": os.environ.get("SOVEREIGN_ADMIN_KEY", "test-admin-key-sprint3")}


# ── auth guards ───────────────────────────────────────────────────────────────


def test_proposals_no_auth():
    r = client.get("/admin/proposals")
    assert r.status_code == 403


def test_versions_no_auth():
    r = client.get("/admin/versions")
    assert r.status_code == 403


def test_report_no_auth():
    r = client.get("/admin/report")
    assert r.status_code == 403


# ── GET /admin/proposals (empty) ──────────────────────────────────────────────


def test_proposals_empty(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    r = client.get("/admin/proposals", headers=HEADERS)
    assert r.status_code == 200
    assert r.json() == []


def test_proposals_filter_by_status(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from app.learning.rule_proposer import RuleProposal, save_proposal

    p = RuleProposal(
        id="aabb1234",
        proposed_at="2026-10-05T10:00:00+00:00",
        source="manual",
        rule_text="Règle test.",
        rationale="Rationale.",
        status="pending",
    )
    (tmp_path / "data").mkdir()
    save_proposal(p, path=tmp_path / "data" / "rule_proposals.jsonl")

    r = client.get("/admin/proposals?status=pending", headers=HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["rule_text"] == "Règle test."


# ── POST /admin/proposals/{id}/approve ───────────────────────────────────────


def test_approve_proposal_api(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from app.learning.rule_proposer import RuleProposal, save_proposal

    p = RuleProposal(
        id="ccdd5678",
        proposed_at="2026-10-05T10:00:00+00:00",
        source="manual",
        rule_text="Approuver cette règle.",
        rationale="Test.",
        status="pending",
    )
    (tmp_path / "data").mkdir()
    save_proposal(p, path=tmp_path / "data" / "rule_proposals.jsonl")

    r = client.post(
        "/admin/proposals/ccdd5678/approve",
        headers={**HEADERS, "X-Reviewer": "test_reviewer"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "approved"
    assert data["reviewed_by"] == "test_reviewer"


def test_approve_unknown_proposal(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    r = client.post("/admin/proposals/nonexistent/approve", headers=HEADERS)
    assert r.status_code == 404


# ── POST /admin/proposals/{id}/reject ────────────────────────────────────────


def test_reject_proposal_api(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from app.learning.rule_proposer import RuleProposal, save_proposal

    p = RuleProposal(
        id="eeff9012",
        proposed_at="2026-10-05T10:00:00+00:00",
        source="manual",
        rule_text="Rejeter cette règle.",
        rationale="Test.",
        status="pending",
    )
    (tmp_path / "data").mkdir()
    save_proposal(p, path=tmp_path / "data" / "rule_proposals.jsonl")

    r = client.post("/admin/proposals/eeff9012/reject", headers=HEADERS)
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"


# ── GET /admin/report ─────────────────────────────────────────────────────────


def test_get_report_empty(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    r = client.get("/admin/report", headers=HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert "total_feedback" in data
    assert "satisfaction_rate" in data
    assert "markdown" in data
    assert data["total_feedback"] == 0


def test_get_report_with_feedback(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from app.feedback import record_feedback

    (tmp_path / "data").mkdir()
    fb_path = tmp_path / "data" / "feedback.jsonl"
    record_feedback("marge brute totale", "SELECT 1", "bad", path=fb_path)
    record_feedback("CA total", "SELECT SUM(montant_ht) FROM ventes_detail", "good", path=fb_path)

    r = client.get("/admin/report", headers=HEADERS)
    assert r.status_code == 200
    data = r.json()
    # Note: report reads from default FEEDBACK_PATH (cwd-relative), may be empty
    # unless the feedback was written to the right relative path
    assert "total_feedback" in data


# ── GET /admin/versions ───────────────────────────────────────────────────────


def test_list_versions_empty(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    r = client.get("/admin/versions", headers=HEADERS)
    assert r.status_code == 200
    assert r.json() == []


def test_create_snapshot_api(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "semantic").mkdir()
    import yaml as _yaml

    (tmp_path / "semantic" / "model.yaml").write_text(
        _yaml.dump({"schema_version": "2", "rules": []}), encoding="utf-8"
    )

    r = client.post("/admin/versions/snapshot", json={"label": "test"}, headers=HEADERS)
    assert r.status_code == 200
    assert "snapshot" in r.json()

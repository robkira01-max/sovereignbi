"""Tests for app/feedback.py — feedback journal and audit journal."""
import json

import pytest

from app.feedback import (
    AuditEntry,
    FeedbackEntry,
    load_audit,
    load_feedback,
    record_audit,
    record_feedback,
)


def test_record_feedback_creates_file(tmp_path):
    p = tmp_path / "feedback.jsonl"
    record_feedback("q", "SELECT 1", "good", path=p)
    assert p.exists()
    assert p.stat().st_size > 0


def test_record_feedback_appends(tmp_path):
    p = tmp_path / "feedback.jsonl"
    record_feedback("q1", "SELECT 1", "good", path=p)
    record_feedback("q2", "SELECT 2", "bad", comment="wrong", path=p)
    lines = [l for l in p.read_text().splitlines() if l.strip()]
    assert len(lines) == 2


def test_record_feedback_invalid_rating(tmp_path):
    p = tmp_path / "feedback.jsonl"
    with pytest.raises(ValueError, match="rating"):
        record_feedback("q", "SELECT 1", "maybe", path=p)


def test_load_feedback_returns_entries(tmp_path):
    p = tmp_path / "feedback.jsonl"
    record_feedback("question A", "SELECT 1", "good", "super", path=p)
    entries = load_feedback(path=p)
    assert len(entries) == 1
    e = entries[0]
    assert isinstance(e, FeedbackEntry)
    assert e.question == "question A"
    assert e.rating == "good"
    assert e.comment == "super"


def test_load_feedback_empty_file(tmp_path):
    p = tmp_path / "feedback.jsonl"
    p.write_text("")
    entries = load_feedback(path=p)
    assert entries == []


def test_load_feedback_missing_file(tmp_path):
    p = tmp_path / "nonexistent.jsonl"
    assert load_feedback(path=p) == []


def test_record_audit_creates_file(tmp_path):
    p = tmp_path / "audit.jsonl"
    record_audit("upload", {"filename": "test.csv"}, path=p)
    assert p.exists()
    data = json.loads(p.read_text().strip())
    assert data["action"] == "upload"
    assert "hash" in data
    assert len(data["hash"]) == 64


def test_record_audit_chain(tmp_path):
    p = tmp_path / "audit.jsonl"
    record_audit("upload", {"f": "a.csv"}, path=p)
    record_audit("ask", {"q": "revenue?"}, path=p)
    lines = [l for l in p.read_text().splitlines() if l.strip()]
    assert len(lines) == 2
    h1 = json.loads(lines[0])["hash"]
    h2 = json.loads(lines[1])["hash"]
    # Hashes must be different (chain links them)
    assert h1 != h2


def test_load_audit_returns_entries(tmp_path):
    p = tmp_path / "audit.jsonl"
    record_audit("upload", {"f": "a.csv"}, path=p)
    record_audit("ask", {"q": "test"}, path=p)
    entries = load_audit(path=p)
    assert len(entries) == 2
    assert all(isinstance(e, AuditEntry) for e in entries)
    assert entries[0].action == "upload"
    assert entries[1].action == "ask"

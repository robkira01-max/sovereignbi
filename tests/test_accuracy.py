"""Tests certificat de précision — Sprint 20."""
import os
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.accuracy.certificate import (
    AccuracyCheck,
    PrecisionCertificate,
    _grade,
    check_answer_references_data,
    check_confidence,
    check_no_error,
    check_sql_has_result,
    check_sql_safety,
    issue_certificate,
    verify_certificate,
)

VIEWER = {"X-Api-Key": "test-viewer-key-s6"}


@pytest.fixture
def client():
    return TestClient(app)


# --- Check unit tests ---

def test_check_sql_safety_select():
    c = check_sql_safety("SELECT * FROM t")
    assert c.passed is True
    assert c.score == 1.0


def test_check_sql_safety_drop():
    c = check_sql_safety("DROP TABLE t")
    assert c.passed is False
    assert c.score == 0.0


def test_check_sql_safety_read_csv():
    c = check_sql_safety("SELECT * FROM read_csv_auto('file.csv')")
    assert c.passed is False


def test_check_has_result_with_data():
    c = check_sql_has_result(["a", "b"], [(1, 2)])
    assert c.passed is True
    assert c.score == 1.0


def test_check_has_result_empty():
    c = check_sql_has_result([], [])
    assert c.passed is False
    assert c.score == 0.0


def test_check_answer_grounded_with_column():
    c = check_answer_references_data("Le total des ventes est 1000", ["ventes", "mois"])
    assert c.passed is True
    assert c.score > 0


def test_check_answer_grounded_with_number():
    c = check_answer_references_data("Il y a 42 résultats", [])
    assert c.passed is True


def test_check_answer_grounded_empty():
    c = check_answer_references_data(None, ["col"])
    assert c.passed is False
    assert c.score == 0.0


def test_check_confidence_high():
    c = check_confidence({"score": 0.85, "label": "high"})
    assert c.passed is True
    assert c.score == 0.85


def test_check_confidence_low():
    c = check_confidence({"score": 0.3, "label": "low"})
    assert c.passed is False


def test_check_confidence_none():
    c = check_confidence(None)
    assert c.passed is False
    assert c.score == 0.0


def test_check_no_error():
    c = check_no_error(None)
    assert c.passed is True
    c2 = check_no_error("Column not found")
    assert c2.passed is False


def test_grade():
    assert _grade(0.95) == "A"
    assert _grade(0.80) == "B"
    assert _grade(0.65) == "C"
    assert _grade(0.45) == "D"
    assert _grade(0.1) == "F"


# --- Certificate issuance ---

def test_issue_certificate_complete():
    cert = issue_certificate(
        question="Quel est le total?",
        sql="SELECT SUM(montant) AS total FROM ventes",
        columns=["total"],
        rows=[(12500,)],
        answer="Le total est 12500",
        error=None,
        confidence={"score": 0.85, "label": "high"},
    )
    assert cert.cert_id
    assert 0.0 <= cert.overall_score <= 1.0
    assert cert.grade in ("A", "B", "C", "D", "F")
    assert cert.signature
    assert cert.valid is True
    assert len(cert.checks) == 5


def test_issue_certificate_with_error():
    cert = issue_certificate(
        question="bad query",
        sql="SELECT * FROM nonexistent",
        columns=[],
        rows=[],
        answer=None,
        error="Table not found",
        confidence=None,
    )
    assert cert.grade in ("D", "F")
    assert cert.overall_score < 0.5


def test_verify_certificate_valid():
    cert = issue_certificate(
        question="test", sql="SELECT 1", columns=["x"], rows=[(1,)],
        answer="1", error=None, confidence={"score": 0.9, "label": "high"},
    )
    assert verify_certificate(cert) is True


def test_verify_certificate_tampered():
    cert = issue_certificate(
        question="test", sql="SELECT 1", columns=["x"], rows=[(1,)],
        answer="1", error=None, confidence={"score": 0.9, "label": "high"},
    )
    cert.overall_score = 0.99
    assert verify_certificate(cert) is False


# --- Route tests ---

def test_certify_route(client):
    r = client.post("/accuracy/certify", json={
        "question": "Quel est le total des ventes ?",
        "sql": "SELECT SUM(montant) FROM ventes",
        "columns": ["montant"],
        "rows": [[12500]],
        "answer": "Le total est 12500",
        "confidence": {"score": 0.85, "label": "high"},
    }, headers=VIEWER)
    assert r.status_code == 200
    data = r.json()
    assert "cert_id" in data
    assert "grade" in data
    assert "signature" in data
    assert data["valid"] is True


def test_verify_route_valid(client):
    cert_r = client.post("/accuracy/certify", json={
        "question": "test",
        "sql": "SELECT 1 AS x",
        "columns": ["x"],
        "rows": [[1]],
        "answer": "1",
    }, headers=VIEWER)
    cert = cert_r.json()

    verify_r = client.post("/accuracy/verify", json=cert, headers=VIEWER)
    assert verify_r.status_code == 200
    assert verify_r.json()["valid"] is True


def test_verify_route_tampered(client):
    cert_r = client.post("/accuracy/certify", json={
        "question": "test",
        "sql": "SELECT 1 AS x",
        "columns": ["x"],
        "rows": [[1]],
        "answer": "1",
    }, headers=VIEWER)
    cert = cert_r.json()
    cert["overall_score"] = 0.99

    verify_r = client.post("/accuracy/verify", json=cert, headers=VIEWER)
    assert verify_r.json()["valid"] is False


def test_certify_requires_viewer(client):
    r = client.post("/accuracy/certify", json={
        "question": "q", "sql": "SELECT 1", "columns": [], "rows": []
    })
    assert r.status_code == 401

"""Tests des routes d'administration /admin/semantic."""
import os

import pytest
import yaml
from fastapi.testclient import TestClient

os.environ.setdefault("SOVEREIGN_ADMIN_KEY", "test-admin-key-sprint3")
os.environ.setdefault("SOVEREIGN_EMBEDDER", "tfidf")

from app.main import app

client = TestClient(app)
HEADERS = {"X-Admin-Key": "test-admin-key-sprint3"}
BAD_HEADERS = {"X-Admin-Key": "wrong-key"}


# ── auth guards ───────────────────────────────────────────────────────────────

def test_get_semantic_no_key():
    r = client.get("/admin/semantic")
    assert r.status_code == 403


def test_get_semantic_wrong_key():
    r = client.get("/admin/semantic", headers=BAD_HEADERS)
    assert r.status_code == 403


def test_get_tables_no_key():
    r = client.get("/admin/semantic/tables")
    assert r.status_code == 403


def test_get_metrics_no_key():
    r = client.get("/admin/semantic/metrics")
    assert r.status_code == 403


# ── GET /admin/semantic ───────────────────────────────────────────────────────

def test_get_semantic_returns_model():
    r = client.get("/admin/semantic", headers=HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert "tables" in data
    assert "metrics" in data
    assert "joins" in data
    assert "rules" in data
    assert data["schema_version"] == "2"


def test_get_semantic_tables_have_columns():
    r = client.get("/admin/semantic", headers=HEADERS)
    tables = r.json()["tables"]
    assert len(tables) >= 5
    for t in tables:
        assert "name" in t
        assert "columns" in t


# ── GET /admin/semantic/tables ────────────────────────────────────────────────

def test_get_tables_list():
    r = client.get("/admin/semantic/tables", headers=HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 5
    for t in data:
        assert "name" in t
        assert "column_count" in t


# ── GET /admin/semantic/metrics ───────────────────────────────────────────────

def test_get_metrics_list():
    r = client.get("/admin/semantic/metrics", headers=HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 5
    names = [m["name"] for m in data]
    assert "chiffre d'affaires" in names


# ── PUT /admin/semantic ───────────────────────────────────────────────────────

def test_put_semantic_roundtrip(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "semantic").mkdir()
    payload = {
        "schema_version": "2",
        "tables": [
            {
                "name": "test_table",
                "description": "Table de test",
                "columns": [{"name": "id", "type": "integer", "description": "PK"}],
            }
        ],
        "metrics": [],
        "joins": [],
        "rules": ["Règle test"],
        "glossary": [],
    }
    r = client.put("/admin/semantic", json=payload, headers=HEADERS)
    assert r.status_code == 200
    assert r.json()["saved"] is True


def test_put_semantic_missing_version():
    r = client.put("/admin/semantic", json={"tables": []}, headers=HEADERS)
    assert r.status_code == 422

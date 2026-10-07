"""Tests HTTP pour les routes /alerts."""
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app, store

EDITOR = {"X-Api-Key": "test-editor-key-s6"}
VIEWER = {"X-Api-Key": "test-viewer-key-s6"}
ADMIN = {"X-Api-Key": "test-admin-key-sprint3"}


@pytest.fixture(autouse=True)
def seed_store():
    store.load_dataframe("sales", pd.DataFrame({"cnt": [150], "revenue": [5000.0]}))
    yield


@pytest.fixture
def client():
    return TestClient(app)


def _create_rule(client, **overrides):
    body = {
        "name": "Test rule",
        "question": "SELECT cnt FROM sales",
        "condition": "gt",
        "threshold": 100.0,
        "column": "cnt",
        "schedule_minutes": 5,
        **overrides,
    }
    return client.post("/alerts/rules", json=body, headers=EDITOR)


def test_create_rule_201(client):
    r = _create_rule(client)
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Test rule"
    assert data["rule_id"]


def test_create_rule_invalid_condition(client):
    r = _create_rule(client, condition="invalid")
    assert r.status_code == 422


def test_create_rule_requires_editor(client):
    body = {
        "name": "x",
        "question": "SELECT cnt FROM sales",
        "condition": "gt",
        "threshold": 0,
        "column": "cnt",
        "schedule_minutes": 5,
    }
    r = client.post("/alerts/rules", json=body, headers=VIEWER)
    assert r.status_code == 403


def test_list_rules(client):
    _create_rule(client)
    r = client.get("/alerts/rules", headers=VIEWER)
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert len(r.json()) >= 1


def test_get_rule_not_found(client):
    r = client.get("/alerts/rules/nonexistent", headers=VIEWER)
    assert r.status_code == 404


def test_delete_rule(client):
    r = _create_rule(client)
    rule_id = r.json()["rule_id"]
    d = client.delete(f"/alerts/rules/{rule_id}", headers=EDITOR)
    assert d.status_code == 200
    assert d.json()["deleted"] == rule_id


def test_run_rule_now(client):
    r = _create_rule(client)
    rule_id = r.json()["rule_id"]
    run = client.post(f"/alerts/rules/{rule_id}/run", headers=EDITOR)
    assert run.status_code == 200
    data = run.json()
    assert data["status"] in ("triggered", "resolved", "error")


def test_history_empty(client):
    r = client.get("/alerts/history", headers=VIEWER)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_webhook_configure_and_get(client):
    r = client.post("/alerts/webhook", json={"url": "http://example.com/hook"}, headers=ADMIN)
    assert r.status_code == 200
    assert r.json()["configured"] is True

    r2 = client.get("/alerts/webhook", headers=ADMIN)
    assert r2.status_code == 200
    assert r2.json()["configured"] is True


def test_webhook_requires_admin(client):
    r = client.post("/alerts/webhook", json={"url": "http://example.com"}, headers=EDITOR)
    assert r.status_code == 403

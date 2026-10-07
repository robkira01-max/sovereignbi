"""Tests E2E API — flux complets via TestClient (équivalent aux tests Playwright sans navigateur)."""
import io
import json
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app, store

VIEWER = {"X-Api-Key": "test-viewer-key-s6"}
EDITOR = {"X-Api-Key": "test-editor-key-s6"}
ADMIN = {"X-Api-Key": "test-admin-key-sprint3"}
NO_KEY = {}


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_store():
    """Ensure a clean state for each test."""
    store.tables.clear()
    yield


# --- Flux 1 : health ---

def test_health_returns_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_v1_health_includes_version(client):
    r = client.get("/api/v1/health")
    assert r.json()["api_version"] == "v1"


def test_x_api_version_header_present(client):
    r = client.get("/health")
    assert r.headers.get("x-api-version") == "v1"


# --- Flux 2 : upload CSV + ask ---

def test_upload_csv_then_table_in_health(client):
    csv = b"product,sales\nWidgets,1000\nGadgets,2000\n"
    files = {"file": ("sales.csv", io.BytesIO(csv), "text/csv")}
    r = client.post("/upload", files=files, headers=EDITOR)
    assert r.status_code == 200
    assert "sales" in r.json()["tables"]
    health = client.get("/health")
    assert "sales" in health.json()["tables"]


def test_ask_without_upload_returns_400(client):
    r = client.post("/ask", json={"question": "How many rows?"}, headers=VIEWER)
    assert r.status_code == 400


def test_ask_without_key_returns_401(client):
    store.load_dataframe("test", pd.DataFrame({"x": [1]}))
    r = client.post("/ask", json={"question": "count"}, headers=NO_KEY)
    assert r.status_code == 401


def test_v1_upload_csv(client):
    csv = b"a,b\n1,2\n3,4\n"
    files = {"file": ("data.csv", io.BytesIO(csv), "text/csv")}
    r = client.post("/api/v1/upload", files=files, headers=VIEWER)
    assert r.status_code == 200
    assert isinstance(r.json()["tables"], list)


def test_upload_unsupported_format(client):
    files = {"file": ("data.json", io.BytesIO(b"{}"), "application/json")}
    r = client.post("/upload", files=files, headers=VIEWER)
    assert r.status_code == 400


# --- Flux 3 : alertes ---

def test_alert_crud_flow(client):
    store.load_dataframe("metrics", pd.DataFrame({"cnt": [200]}))
    # Create
    create = client.post("/alerts/rules", json={
        "name": "High count",
        "question": "SELECT cnt FROM metrics",
        "condition": "gt",
        "threshold": 100.0,
        "column": "cnt",
        "schedule_minutes": 5,
    }, headers=EDITOR)
    assert create.status_code == 200
    rule_id = create.json()["rule_id"]

    # List
    lst = client.get("/alerts/rules", headers=VIEWER)
    assert any(r["rule_id"] == rule_id for r in lst.json())

    # Run now
    run = client.post(f"/alerts/rules/{rule_id}/run", headers=EDITOR)
    assert run.status_code == 200
    assert run.json()["status"] == "triggered"

    # Delete
    delete = client.delete(f"/alerts/rules/{rule_id}", headers=EDITOR)
    assert delete.status_code == 200


# --- Flux 4 : export ---

def test_export_excel_flow(client):
    store.load_dataframe("sales", pd.DataFrame({"item": ["a", "b"], "qty": [10, 20]}))
    mock_graph = MagicMock()
    mock_graph.invoke.return_value = {
        "sql": "SELECT * FROM sales",
        "columns": ["item", "qty"],
        "rows": [("a", 10), ("b", 20)],
        "answer": "2 items",
        "error": None,
    }
    with patch.object(app.state, "get_graph", new=lambda: mock_graph):
        r = client.post("/export/excel", json={"question": "all sales"}, headers=VIEWER)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/vnd.openxmlformats")


# --- Flux 5 : compliance ---

def test_compliance_privacy_notice(client):
    r = client.get("/compliance/notice", headers=VIEWER)
    assert r.status_code == 200
    assert "rights" in r.json()


def test_compliance_consent_flow(client):
    uid = "e2e-test-user"
    grant = client.post("/compliance/consent", json={
        "user_id": uid, "purpose": "analytics", "granted": True
    }, headers=EDITOR)
    assert grant.status_code == 200

    lst = client.get(f"/compliance/consent/{uid}", headers=VIEWER)
    assert len(lst.json()) >= 1

    combined = {**EDITOR, "content-type": "application/json"}
    withdraw = client.request("DELETE", "/compliance/consent",
                              content=json.dumps({"user_id": uid, "purpose": "analytics"}),
                              headers=combined)
    assert withdraw.status_code == 200
    assert withdraw.json()["withdrawn"] >= 1


# --- Flux 6 : orgs multi-tenant ---

def test_org_create_and_list(client):
    create = client.post("/orgs", json={"name": "E2E Corp", "plan": "free"}, headers=ADMIN)
    assert create.status_code in (200, 201)
    org_id = create.json()["org_id"]

    lst = client.get("/orgs", headers=ADMIN)
    assert any(o["org_id"] == org_id for o in lst.json()["orgs"])

    get_one = client.get(f"/orgs/{org_id}", headers=ADMIN)
    assert get_one.status_code == 200
    assert get_one.json()["org_id"] == org_id

"""Tests conformité Loi 25 / PIPEDA — Sprint 15."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.compliance.models import (
    record_consent,
    withdraw_consent,
    list_consents,
    create_subject_request,
    list_requests,
    update_request_status,
    add_inventory_item,
    list_inventory,
)

VIEWER = {"X-Api-Key": "test-viewer-key-s6"}
EDITOR = {"X-Api-Key": "test-editor-key-s6"}
ADMIN = {"X-Api-Key": "test-admin-key-sprint3"}


@pytest.fixture
def client():
    return TestClient(app)


# --- Unit tests ---

def test_record_consent(tmp_path):
    c = record_consent("u1", "analytics", True, path=tmp_path / "c.jsonl")
    assert c.consent_id
    assert c.granted is True
    assert c.withdrawn_at is None


def test_withdraw_consent(tmp_path):
    p = tmp_path / "c.jsonl"
    record_consent("u1", "analytics", True, path=p)
    count = withdraw_consent("u1", "analytics", path=p)
    assert count == 1
    consents = list_consents("u1", path=p)
    assert all(c.withdrawn_at is not None for c in consents if c.purpose == "analytics")


def test_withdraw_consent_no_match(tmp_path):
    p = tmp_path / "c.jsonl"
    record_consent("u1", "analytics", True, path=p)
    count = withdraw_consent("u1", "marketing", path=p)
    assert count == 0


def test_list_consents_isolation(tmp_path):
    p = tmp_path / "c.jsonl"
    record_consent("u1", "analytics", True, path=p)
    record_consent("u2", "analytics", False, path=p)
    assert len(list_consents("u1", path=p)) == 1
    assert len(list_consents("u2", path=p)) == 1


def test_create_subject_request(tmp_path):
    r = create_subject_request("u1", "access", path=tmp_path / "r.jsonl")
    assert r.request_id
    assert r.status == "pending"
    assert r.request_type == "access"


def test_create_subject_request_invalid_type(tmp_path):
    with pytest.raises(ValueError):
        create_subject_request("u1", "invalid_type", path=tmp_path / "r.jsonl")


def test_list_requests_filter(tmp_path):
    p = tmp_path / "r.jsonl"
    create_subject_request("u1", "delete", path=p)
    create_subject_request("u2", "export", path=p)
    assert len(list_requests("u1", path=p)) == 1
    assert len(list_requests(path=p)) == 2


def test_update_request_status(tmp_path):
    p = tmp_path / "r.jsonl"
    r = create_subject_request("u1", "delete", path=p)
    updated = update_request_status(r.request_id, "completed", path=p)
    assert updated.status == "completed"
    assert updated.completed_at is not None


def test_update_request_not_found(tmp_path):
    p = tmp_path / "r.jsonl"
    with pytest.raises(KeyError):
        update_request_status("nonexistent", "completed", path=p)


def test_add_inventory_item(tmp_path):
    p = tmp_path / "inv.jsonl"
    item = add_inventory_item("PII", "Emails utilisateurs", "90d", "contrat", "DuckDB local", path=p)
    assert item.item_id
    assert item.retention_policy == "90d"


def test_add_inventory_item_invalid_retention(tmp_path):
    p = tmp_path / "inv.jsonl"
    with pytest.raises(ValueError):
        add_inventory_item("PII", "x", "10y", "contrat", "local", path=p)


def test_list_inventory(tmp_path):
    p = tmp_path / "inv.jsonl"
    add_inventory_item("PII", "desc1", "1y", "loi", "local", path=p)
    add_inventory_item("logs", "desc2", "30d", "légitimité", "local", path=p)
    items = list_inventory(path=p)
    assert len(items) == 2


# --- Route tests ---

def test_record_consent_route(client):
    r = client.post("/compliance/consent", json={
        "user_id": "u1", "purpose": "analytics", "granted": True
    }, headers=EDITOR)
    assert r.status_code == 200
    assert r.json()["granted"] is True


def test_get_consents_route(client):
    client.post("/compliance/consent", json={
        "user_id": "u-route", "purpose": "ai_processing", "granted": True
    }, headers=EDITOR)
    r = client.get("/compliance/consent/u-route", headers=VIEWER)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_create_dsr_route(client):
    r = client.post("/compliance/requests", json={
        "user_id": "u1", "request_type": "access"
    }, headers=VIEWER)
    assert r.status_code == 200
    data = r.json()
    assert data["request_type"] == "access"
    assert data["status"] == "pending"


def test_create_dsr_invalid_type_route(client):
    r = client.post("/compliance/requests", json={
        "user_id": "u1", "request_type": "invalid"
    }, headers=VIEWER)
    assert r.status_code == 422


def test_list_dsrs_requires_admin(client):
    r = client.get("/compliance/requests", headers=EDITOR)
    assert r.status_code == 403


def test_add_inventory_route(client):
    r = client.post("/compliance/inventory", json={
        "data_category": "PII",
        "description": "Données utilisateur",
        "retention_policy": "1y",
        "legal_basis": "contrat",
        "location": "DuckDB local",
    }, headers=ADMIN)
    assert r.status_code == 200
    assert r.json()["retention_policy"] == "1y"


def test_get_inventory_route(client):
    r = client.get("/compliance/inventory", headers=VIEWER)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_privacy_notice_route(client):
    r = client.get("/compliance/notice", headers=VIEWER)
    assert r.status_code == 200
    data = r.json()
    assert "Loi 25" in data["applicable_laws"][0]
    assert "rights" in data

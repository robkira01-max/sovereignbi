"""Tests pour la gestion multi-tenant des organisations."""
from __future__ import annotations

import os
import pytest
from fastapi.testclient import TestClient

_ADMIN_KEY = os.environ.get("SOVEREIGN_ADMIN_KEY", "test-admin-key-sprint3")
_EDITOR_KEY = os.environ.get("SOVEREIGN_EDITOR_KEY", "test-editor-key-s6")
_VIEWER_KEY = os.environ.get("SOVEREIGN_VIEWER_KEY", "test-viewer-key-s6")

_A = {"X-Api-Key": _ADMIN_KEY}
_E = {"X-Api-Key": _EDITOR_KEY}
_V = {"X-Api-Key": _VIEWER_KEY}


@pytest.fixture
def client(tmp_path):
    """Fresh app with isolated org registry per test."""
    import app.main as m
    from app.multitenancy.org import OrgRegistry

    original = m.app.state.org_registry
    m.app.state.org_registry = OrgRegistry(path=str(tmp_path / "orgs.jsonl"))
    yield TestClient(m.app)
    m.app.state.org_registry = original


# ── OrgRegistry unit tests ────────────────────────────────────────────────────

def test_create_org_returns_org(tmp_path):
    from app.multitenancy.org import OrgRegistry
    reg = OrgRegistry(path=str(tmp_path / "orgs.jsonl"))
    org = reg.create(name="Acme", owner_key="key-owner")
    assert org.org_id.startswith("org_")
    assert org.name == "Acme"
    assert org.owner_key == "key-owner"
    assert org.created_at != ""


def test_get_org_by_id(tmp_path):
    from app.multitenancy.org import OrgRegistry
    reg = OrgRegistry(path=str(tmp_path / "orgs.jsonl"))
    org = reg.create("TestCo", "owner-key")
    found = reg.get(org.org_id)
    assert found is not None
    assert found.org_id == org.org_id


def test_get_org_missing_returns_none(tmp_path):
    from app.multitenancy.org import OrgRegistry
    reg = OrgRegistry(path=str(tmp_path / "orgs.jsonl"))
    assert reg.get("org_notexist") is None


def test_get_by_key_owner(tmp_path):
    from app.multitenancy.org import OrgRegistry
    reg = OrgRegistry(path=str(tmp_path / "orgs.jsonl"))
    org = reg.create("Firm", "owner-key-x")
    found = reg.get_by_key("owner-key-x")
    assert found is not None
    assert found.org_id == org.org_id


def test_get_by_key_member(tmp_path):
    from app.multitenancy.org import OrgRegistry
    reg = OrgRegistry(path=str(tmp_path / "orgs.jsonl"))
    org = reg.create("Firm", "owner-key-y")
    reg.add_member(org.org_id, "member-key-y", "owner-key-y")
    found = reg.get_by_key("member-key-y")
    assert found is not None
    assert found.org_id == org.org_id


def test_get_by_key_unknown_returns_none(tmp_path):
    from app.multitenancy.org import OrgRegistry
    reg = OrgRegistry(path=str(tmp_path / "orgs.jsonl"))
    assert reg.get_by_key("unknown-key") is None


def test_list_orgs_empty(tmp_path):
    from app.multitenancy.org import OrgRegistry
    reg = OrgRegistry(path=str(tmp_path / "orgs.jsonl"))
    assert reg.list_orgs("some-key") == []


def test_list_orgs_owner(tmp_path):
    from app.multitenancy.org import OrgRegistry
    reg = OrgRegistry(path=str(tmp_path / "orgs.jsonl"))
    org = reg.create("Corp", "key-corp-owner")
    orgs = reg.list_orgs("key-corp-owner")
    assert len(orgs) == 1
    assert orgs[0].org_id == org.org_id


def test_add_member_ok(tmp_path):
    from app.multitenancy.org import OrgRegistry
    reg = OrgRegistry(path=str(tmp_path / "orgs.jsonl"))
    org = reg.create("X", "owner")
    updated = reg.add_member(org.org_id, "member-1", "owner")
    assert "member-1" in updated.member_keys


def test_add_member_non_owner_raises(tmp_path):
    from app.multitenancy.org import OrgRegistry
    reg = OrgRegistry(path=str(tmp_path / "orgs.jsonl"))
    org = reg.create("Y", "real-owner")
    with pytest.raises(PermissionError):
        reg.add_member(org.org_id, "x", "not-owner")


def test_remove_member_ok(tmp_path):
    from app.multitenancy.org import OrgRegistry
    reg = OrgRegistry(path=str(tmp_path / "orgs.jsonl"))
    org = reg.create("Z", "owner-z")
    reg.add_member(org.org_id, "mem", "owner-z")
    updated = reg.remove_member(org.org_id, "mem", "owner-z")
    assert "mem" not in updated.member_keys


def test_remove_owner_raises(tmp_path):
    from app.multitenancy.org import OrgRegistry
    reg = OrgRegistry(path=str(tmp_path / "orgs.jsonl"))
    org = reg.create("W", "owner-w")
    with pytest.raises(ValueError):
        reg.remove_member(org.org_id, "owner-w", "owner-w")


def test_registry_persistence(tmp_path):
    from app.multitenancy.org import OrgRegistry
    path = str(tmp_path / "orgs.jsonl")
    reg = OrgRegistry(path=path)
    org = reg.create("Persistent", "pkey")
    # reload
    reg2 = OrgRegistry(path=path)
    found = reg2.get(org.org_id)
    assert found is not None
    assert found.name == "Persistent"


# ── isolation helpers ─────────────────────────────────────────────────────────

def test_require_same_org_true(tmp_path):
    from app.multitenancy.org import OrgRegistry
    from app.multitenancy.isolation import require_same_org
    reg = OrgRegistry(path=str(tmp_path / "orgs.jsonl"))
    org = reg.create("A", "key-a1")
    reg.add_member(org.org_id, "key-a2", "key-a1")
    assert require_same_org("key-a1", "key-a2", reg) is True


def test_require_same_org_false_different_orgs(tmp_path):
    from app.multitenancy.org import OrgRegistry
    from app.multitenancy.isolation import require_same_org
    reg = OrgRegistry(path=str(tmp_path / "orgs.jsonl"))
    reg.create("OrgA", "key-oa")
    reg.create("OrgB", "key-ob")
    assert require_same_org("key-oa", "key-ob", reg) is False


def test_require_same_org_false_unknown(tmp_path):
    from app.multitenancy.org import OrgRegistry
    from app.multitenancy.isolation import require_same_org
    reg = OrgRegistry(path=str(tmp_path / "orgs.jsonl"))
    assert require_same_org("unknown-a", "unknown-b", reg) is False


# ── REST endpoints ────────────────────────────────────────────────────────────

def test_create_org_admin_only(client):
    r = client.post("/orgs", json={"name": "TestFirm"}, headers=_V)
    assert r.status_code == 403


def test_create_org_success(client):
    r = client.post("/orgs", json={"name": "Acme Law"}, headers=_A)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Acme Law"
    assert data["org_id"].startswith("org_")


def test_list_orgs_empty(client):
    r = client.get("/orgs", headers=_V)
    assert r.status_code == 200
    assert r.json()["orgs"] == []


def test_list_orgs_shows_own_org(client):
    client.post("/orgs", json={"name": "MyFirm"}, headers=_A)
    r = client.get("/orgs", headers=_A)
    assert r.status_code == 200
    orgs = r.json()["orgs"]
    assert len(orgs) >= 1


def test_get_org_not_found(client):
    r = client.get("/orgs/org_notexist", headers=_A)
    assert r.status_code == 404


def test_get_org_found(client):
    resp = client.post("/orgs", json={"name": "GetMe"}, headers=_A)
    org_id = resp.json()["org_id"]
    r = client.get(f"/orgs/{org_id}", headers=_A)
    assert r.status_code == 200
    assert r.json()["name"] == "GetMe"


def test_add_member_via_route(client):
    resp = client.post("/orgs", json={"name": "Firm"}, headers=_A)
    org_id = resp.json()["org_id"]
    r = client.post(f"/orgs/{org_id}/members", json={"key": "new-member-key"}, headers=_A)
    assert r.status_code == 200
    assert "new-member-key" in r.json()["member_keys"]


def test_remove_member_via_route(client):
    resp = client.post("/orgs", json={"name": "Firm2"}, headers=_A)
    org_id = resp.json()["org_id"]
    client.post(f"/orgs/{org_id}/members", json={"key": "to-remove"}, headers=_A)
    r = client.delete(f"/orgs/{org_id}/members/to-remove", headers=_A)
    assert r.status_code == 200
    assert "to-remove" not in r.json()["member_keys"]

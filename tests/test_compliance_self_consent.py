"""Self-service consent (CGU / privacy acceptance) and AI-aware privacy notice."""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.auth import router as auth_router
from app.auth import security as sec
from app.compliance import models as cmodels

PW = "correct-horse-battery"
VIEWER_KEY = {"X-Api-Key": "test-viewer-key-s6"}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("SOVEREIGN_AUTH_DB", str(tmp_path / "auth.db"))
    monkeypatch.setattr(cmodels, "CONSENT_PATH", tmp_path / "consents.jsonl")
    # record_consent's default argument was bound at import time: patch it explicitly
    monkeypatch.setattr(cmodels.record_consent, "__defaults__", (None, tmp_path / "consents.jsonl"))
    auth_router._throttle.reset()
    sec.init_auth_db()
    from app.main import app

    with TestClient(app) as c:
        yield c
    auth_router._throttle.reset()


def _bearer(client, email, role="viewer"):
    sec.create_user(email, PW, role)
    token = client.post("/auth/login", json={"email": email, "password": PW}).json()["token"]
    return {"Authorization": f"Bearer {token}"}


def _lines(tmp_path):
    p = tmp_path / "consents.jsonl"
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []


def test_viewer_can_record_own_acceptance(client, tmp_path):
    h = _bearer(client, "viewer@example.org")
    r = client.post("/compliance/consent/self", json={"purpose": "cgu:2026-11", "granted": True}, headers=h)
    assert r.status_code == 200
    rec = _lines(tmp_path)[-1]
    assert rec["user_id"] == "viewer@example.org"
    assert rec["purpose"] == "cgu:2026-11"
    assert rec["granted"] is True
    assert rec["ip_address"] is None


def test_identity_comes_from_session_not_body(client, tmp_path):
    h = _bearer(client, "a@example.org")
    r = client.post(
        "/compliance/consent/self",
        json={"purpose": "cgu:2026-11", "user_id": "victim@example.org"},
        headers=h,
    )
    assert r.status_code == 200
    assert _lines(tmp_path)[-1]["user_id"] == "a@example.org"


@pytest.mark.parametrize("purpose", ["analytics", "cgu", "cgu:2026-1", "x" * 200, "cgu:2026-11\nx"])
def test_purpose_allowlist(client, purpose):
    h = _bearer(client, "p@example.org")
    r = client.post("/compliance/consent/self", json={"purpose": purpose}, headers=h)
    assert r.status_code == 422


def test_api_key_has_no_user_identity(client):
    r = client.post("/compliance/consent/self", json={"purpose": "cgu:2026-11"}, headers=VIEWER_KEY)
    assert r.status_code == 400


def test_requires_authentication(client):
    assert client.post("/compliance/consent/self", json={"purpose": "cgu:2026-11"}).status_code == 401
    bad = {"Authorization": "Bearer not-a-session"}
    assert client.post("/compliance/consent/self", json={"purpose": "cgu:2026-11"}, headers=bad).status_code == 401


def test_notice_reflects_local_llm(client, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    n = client.get("/compliance/notice", headers=VIEWER_KEY).json()
    assert "aucune donnée transmise" in n["data_location"]
    assert "local" in n["purposes"][1]["description"].lower()


def test_notice_discloses_external_llm(client, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "kimi")
    n = client.get("/compliance/notice", headers=VIEWER_KEY).json()
    assert "externe" in n["data_location"]
    assert "kimi" in n["purposes"][1]["description"]
    assert "aucune donnée transmise" not in n["data_location"]

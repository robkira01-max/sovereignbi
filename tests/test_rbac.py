"""Tests RBAC : viewer < editor < admin.

Keys are set in conftest.py:
  SOVEREIGN_VIEWER_KEY  = "test-viewer-key-s6"
  SOVEREIGN_EDITOR_KEY  = "test-editor-key-s6"
  SOVEREIGN_ADMIN_KEY   = "test-admin-key-sprint3"
"""
import os

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.security.rbac import ROLES, RequireRole, get_role_from_key

client = TestClient(app)

_VIEWER_KEY = os.environ.get("SOVEREIGN_VIEWER_KEY", "test-viewer-key-s6")
_EDITOR_KEY = os.environ.get("SOVEREIGN_EDITOR_KEY", "test-editor-key-s6")
_ADMIN_KEY = os.environ.get("SOVEREIGN_ADMIN_KEY", "test-admin-key-sprint3")

_V = {"X-Api-Key": _VIEWER_KEY}
_E = {"X-Api-Key": _EDITOR_KEY}
_A_ADMIN = {"X-Admin-Key": _ADMIN_KEY}


# ── Unit: get_role_from_key ───────────────────────────────────────────────────

def test_viewer_key_returns_viewer():
    assert get_role_from_key(_VIEWER_KEY) == "viewer"


def test_editor_key_returns_editor():
    assert get_role_from_key(_EDITOR_KEY) == "editor"


def test_admin_key_returns_admin():
    assert get_role_from_key(_ADMIN_KEY) == "admin"


def test_unknown_key_returns_none():
    assert get_role_from_key("bogus-key-xyz") is None


def test_empty_key_returns_none():
    assert get_role_from_key("") is None


def test_role_hierarchy():
    assert ROLES["viewer"] < ROLES["editor"] < ROLES["admin"]


# ── Unit: RequireRole ─────────────────────────────────────────────────────────

def test_require_role_invalid_role_raises():
    with pytest.raises(ValueError):
        RequireRole("superuser")


# ── Integration: /health is public ───────────────────────────────────────────

def test_health_public_no_key():
    r = client.get("/health")
    assert r.status_code == 200


def test_health_public_with_bad_key():
    r = client.get("/health", headers={"X-Api-Key": "garbage"})
    assert r.status_code == 200


# ── Integration: /ask requires viewer+ ───────────────────────────────────────

def test_ask_no_key_returns_401():
    r = client.post("/ask", json={"question": "CA total ?"})
    assert r.status_code == 401


def test_ask_bad_key_returns_401():
    r = client.post("/ask", json={"question": "CA ?"}, headers={"X-Api-Key": "bad"})
    assert r.status_code == 401


def test_ask_viewer_key_returns_400_not_401():
    # 400 = no data loaded, not 401 — auth passed
    r = client.post("/ask", json={"question": "CA ?"}, headers=_V)
    assert r.status_code == 400


# ── Integration: /upload requires viewer+ ────────────────────────────────────

def test_upload_no_key_returns_401():
    r = client.post("/upload", files={"file": ("f.csv", b"a,b\n1,2", "text/csv")})
    assert r.status_code == 401


def test_upload_viewer_key_allowed():
    r = client.post("/upload", files={"file": ("f.csv", b"a,b\n1,2", "text/csv")},
                    headers=_V)
    assert r.status_code == 200


# ── Integration: /admin requires X-Admin-Key ─────────────────────────────────

def test_admin_no_key_returns_403():
    r = client.get("/admin/semantic")
    assert r.status_code == 403


def test_admin_wrong_key_returns_403():
    r = client.get("/admin/semantic", headers={"X-Admin-Key": "wrong"})
    assert r.status_code == 403


def test_admin_correct_admin_key_returns_200():
    r = client.get("/admin/semantic", headers=_A_ADMIN)
    assert r.status_code == 200


# ── Integration: dashboards RBAC ─────────────────────────────────────────────

def test_dashboards_no_key_returns_401():
    r = client.get("/dashboards")
    assert r.status_code == 401


def test_dashboards_viewer_can_read():
    r = client.get("/dashboards", headers=_V)
    assert r.status_code == 200


def test_dashboards_viewer_cannot_create():
    body = {"id": "rbac_test_dash", "title": "T", "scope": "personal", "tiles": [], "theme": {}}
    r = client.post("/dashboards", json=body, headers=_V)
    assert r.status_code == 403


def test_dashboards_editor_can_create():
    body = {"id": "rbac_editor_dash2", "title": "T", "scope": "personal", "tiles": [], "theme": {}}
    r = client.post("/dashboards", json=body, headers=_E)
    assert r.status_code == 200

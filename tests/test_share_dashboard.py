"""Tests for dashboard share tokens and public /shared/ routes."""
from __future__ import annotations

import os
import time
from pathlib import Path

import pytest
import yaml

os.environ.setdefault("SOVEREIGN_EMBEDDER", "tfidf")

VIEWER = {"X-Api-Key": "test-viewer-key-s6"}
EDITOR = {"X-Api-Key": "test-editor-key-s6"}


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


def _write_yaml(tmp_path: Path, dash_id: str) -> None:
    tile = {"id": "kpi1", "type": "kpi", "title": "T", "sql_pinned": "SELECT 42.0 AS v"}
    data = {
        "id": dash_id, "title": "T", "scope": "personal",
        "tiles": [tile], "created_at": "", "updated_at": "",
        "theme": {"primary_color": "#1a4a8c", "font": "sans-serif", "logo_url": ""},
    }
    (tmp_path / f"{dash_id}.yaml").write_text(yaml.safe_dump(data))


# ── Unit tests for share.py ──────────────────────────────────────────────────

def test_generate_and_validate(tmp_path):
    from app.dashboards.share import generate_share_token, validate_share_token
    path = tmp_path / "shares.json"
    result = generate_share_token("my-dash", ttl=3600, path=path)
    token = result["token"]
    assert validate_share_token(token, path=path) == "my-dash"


def test_expired_token_returns_none(tmp_path):
    from app.dashboards.share import generate_share_token, validate_share_token
    path = tmp_path / "shares2.json"
    result = generate_share_token("my-dash", ttl=1, path=path)
    token = result["token"]
    time.sleep(1.1)
    assert validate_share_token(token, path=path) is None


def test_invalid_token_returns_none(tmp_path):
    from app.dashboards.share import validate_share_token
    path = tmp_path / "shares3.json"
    assert validate_share_token("not.a.real.token", path=path) is None


def test_revoke_token(tmp_path):
    from app.dashboards.share import generate_share_token, validate_share_token, revoke_share_token
    path = tmp_path / "shares4.json"
    result = generate_share_token("my-dash", ttl=3600, path=path)
    token = result["token"]
    assert revoke_share_token(token, path=path) is True
    assert validate_share_token(token, path=path) is None


# ── Route tests ──────────────────────────────────────────────────────────────

def test_create_share_route(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    shares_path = tmp_path / "s.json"
    monkeypatch.setattr("app.dashboards.share._SHARES_PATH", shares_path)
    _write_yaml(tmp_path, "d-share-1")
    r = client.post("/dashboards/d-share-1/share", headers=EDITOR)
    assert r.status_code == 201
    data = r.json()
    assert "token" in data
    assert data["dashboard_id"] == "d-share-1"
    assert "/dashboards/shared/" in data["url_path"]


def test_public_shared_route_no_auth(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    shares_path = tmp_path / "s2.json"
    monkeypatch.setattr("app.dashboards.share._SHARES_PATH", shares_path)
    _write_yaml(tmp_path, "d-share-2")
    r = client.post("/dashboards/d-share-2/share", headers=EDITOR)
    token = r.json()["token"]
    # Access without any auth header
    r2 = client.get(f"/dashboards/shared/{token}")
    assert r2.status_code == 200
    assert r2.json()["id"] == "d-share-2"


def test_public_tile_data_no_auth(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    shares_path = tmp_path / "s3.json"
    monkeypatch.setattr("app.dashboards.share._SHARES_PATH", shares_path)
    _write_yaml(tmp_path, "d-share-3")
    r = client.post("/dashboards/d-share-3/share", headers=EDITOR)
    token = r.json()["token"]
    r2 = client.get(f"/dashboards/shared/{token}/tiles/kpi1/data")
    assert r2.status_code == 200
    assert "rows" in r2.json()


def test_invalid_share_token_403(client):
    r = client.get("/dashboards/shared/invalid.token.here")
    assert r.status_code == 403


def test_share_requires_editor(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    _write_yaml(tmp_path, "d-share-auth")
    r = client.post("/dashboards/d-share-auth/share", headers=VIEWER)
    assert r.status_code == 403

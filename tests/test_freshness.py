"""Tests for tile freshness tracking and /freshness route."""
from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

os.environ.setdefault("SOVEREIGN_EMBEDDER", "tfidf")

VIEWER = {"X-Api-Key": "test-viewer-key-s6"}


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


# ── Unit tests for tile_cache ─────────────────────────────────────────────────

def test_age_none_before_execution():
    from app.dashboards.tile_cache import age_seconds, clear_all
    clear_all()
    assert age_seconds("dash-fresh", "kpi1") is None


def test_age_seconds_after_record():
    from app.dashboards.tile_cache import record_execution, age_seconds, clear_all
    clear_all()
    record_execution("dash-fresh", "kpi1")
    age = age_seconds("dash-fresh", "kpi1")
    assert age is not None
    assert 0.0 <= age < 2.0


# ── Route tests ───────────────────────────────────────────────────────────────

def test_freshness_stale_before_data_fetch(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    from app.dashboards import tile_cache
    tile_cache.clear_all()
    _write_yaml(tmp_path, "d-fresh-1")
    r = client.get("/dashboards/d-fresh-1/tiles/kpi1/freshness", headers=VIEWER)
    assert r.status_code == 200
    data = r.json()
    assert data["stale"] is True
    assert data["age_seconds"] is None


def test_freshness_fresh_after_data_fetch(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    from app.dashboards import tile_cache
    tile_cache.clear_all()
    _write_yaml(tmp_path, "d-fresh-2")
    client.get("/dashboards/d-fresh-2/tiles/kpi1/data", headers=VIEWER)
    r = client.get("/dashboards/d-fresh-2/tiles/kpi1/freshness", headers=VIEWER)
    assert r.status_code == 200
    data = r.json()
    assert data["stale"] is False
    assert data["age_seconds"] is not None
    assert data["age_seconds"] < 5.0


def test_freshness_missing_dashboard(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    r = client.get("/dashboards/ghost-fresh/tiles/kpi1/freshness", headers=VIEWER)
    assert r.status_code == 404


def test_freshness_requires_auth(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    _write_yaml(tmp_path, "d-fresh-auth")
    r = client.get("/dashboards/d-fresh-auth/tiles/kpi1/freshness")
    assert r.status_code == 401

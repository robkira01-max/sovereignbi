"""Tests for dashboard favorites (toggle + list)."""
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
    data = {
        "id": dash_id, "title": "T", "scope": "personal",
        "tiles": [], "created_at": "", "updated_at": "",
        "theme": {"primary_color": "#1a4a8c", "font": "sans-serif", "logo_url": ""},
    }
    (tmp_path / f"{dash_id}.yaml").write_text(yaml.safe_dump(data))


# ── Unit tests for favorites helper ─────────────────────────────────────────

def test_toggle_adds_and_removes(tmp_path):
    from app.dashboards.favorites import toggle_favorite, get_favorites
    path = tmp_path / "fav.json"
    assert toggle_favorite("key1", "dash-a", path) is True
    assert "dash-a" in get_favorites("key1", path)
    assert toggle_favorite("key1", "dash-a", path) is False
    assert "dash-a" not in get_favorites("key1", path)


def test_different_users_isolated(tmp_path):
    from app.dashboards.favorites import toggle_favorite, get_favorites
    path = tmp_path / "fav2.json"
    toggle_favorite("user1", "dash-x", path)
    toggle_favorite("user2", "dash-y", path)
    assert get_favorites("user1", path) == ["dash-x"]
    assert get_favorites("user2", path) == ["dash-y"]


# ── Route tests ──────────────────────────────────────────────────────────────

def test_toggle_favorite_route(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    favs_path = tmp_path / "favorites.json"
    monkeypatch.setattr("app.dashboards.favorites._FAVORITES_PATH", favs_path)
    _write_yaml(tmp_path, "d-fav-1")
    r = client.post("/dashboards/d-fav-1/favorite", headers=VIEWER)
    assert r.status_code == 200
    assert r.json()["is_favorite"] is True
    # Toggle off
    r2 = client.post("/dashboards/d-fav-1/favorite", headers=VIEWER)
    assert r2.json()["is_favorite"] is False


def test_list_dashboards_includes_is_favorite(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    favs_path = tmp_path / "fav_list.json"
    monkeypatch.setattr("app.dashboards.favorites._FAVORITES_PATH", favs_path)
    _write_yaml(tmp_path, "d-fav-2")
    _write_yaml(tmp_path, "d-fav-3")
    # Favorite one dashboard
    client.post("/dashboards/d-fav-2/favorite", headers=VIEWER)
    r = client.get("/dashboards", headers=VIEWER)
    assert r.status_code == 200
    items = {d["id"]: d for d in r.json()["dashboards"]}
    assert items["d-fav-2"]["is_favorite"] is True
    assert items["d-fav-3"]["is_favorite"] is False


def test_toggle_missing_404(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    r = client.post("/dashboards/ghost-fav/favorite", headers=VIEWER)
    assert r.status_code == 404

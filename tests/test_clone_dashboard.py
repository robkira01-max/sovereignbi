"""Tests for POST /dashboards/{id}/clone."""
from __future__ import annotations

import os
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
    data = {
        "id": dash_id, "title": "Dashboard Test", "scope": "personal",
        "tiles": [
            {"id": "kpi1", "type": "kpi", "title": "KPI A", "sql_pinned": "SELECT 1"},
            {"id": "bar1", "type": "bar", "title": "Graphe B"},
        ],
        "theme": {"primary_color": "#1a4a8c", "font": "sans-serif", "logo_url": ""},
        "created_at": "2026-01-01", "updated_at": "2026-01-01",
    }
    (tmp_path / f"{dash_id}.yaml").write_text(yaml.safe_dump(data))


def test_clone_creates_new_file(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    _write_yaml(tmp_path, "d-src")
    r = client.post("/dashboards/d-src/clone", headers=EDITOR)
    assert r.status_code == 201
    data = r.json()
    assert data["id"] == "d-src-copy"
    assert "(copie)" in data["title"]
    assert (tmp_path / "d-src-copy.yaml").exists()


def test_clone_custom_id_and_title(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    _write_yaml(tmp_path, "d-src2")
    r = client.post(
        "/dashboards/d-src2/clone",
        json={"new_id": "d-region-b", "title": "Région B"},
        headers=EDITOR,
    )
    assert r.status_code == 201
    data = r.json()
    assert data["id"] == "d-region-b"
    assert data["title"] == "Région B"
    assert (tmp_path / "d-region-b.yaml").exists()


def test_clone_copies_all_tiles(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    _write_yaml(tmp_path, "d-src3")
    client.post("/dashboards/d-src3/clone", json={"new_id": "d-clone3"}, headers=EDITOR)
    raw = (tmp_path / "d-clone3.yaml").read_text()
    loaded = yaml.safe_load(raw)
    assert len(loaded["tiles"]) == 2
    assert loaded["tiles"][0]["id"] == "kpi1"


def test_clone_conflict_409(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    _write_yaml(tmp_path, "d-src4")
    _write_yaml(tmp_path, "d-src4-copy")
    r = client.post("/dashboards/d-src4/clone", headers=EDITOR)
    assert r.status_code == 409


def test_clone_missing_404(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    r = client.post("/dashboards/ghost-clone/clone", headers=EDITOR)
    assert r.status_code == 404


def test_clone_invalid_new_id(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    _write_yaml(tmp_path, "d-src5")
    r = client.post(
        "/dashboards/d-src5/clone",
        json={"new_id": "has spaces!"},
        headers=EDITOR,
    )
    assert r.status_code == 422


def test_clone_requires_editor(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    _write_yaml(tmp_path, "d-src6")
    r = client.post("/dashboards/d-src6/clone", headers=VIEWER)
    assert r.status_code == 403

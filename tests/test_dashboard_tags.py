"""Tests for dashboard tags — PUT /dashboards/{id}/tags + GET ?tag= filter."""
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


def _write_yaml(tmp_path: Path, dash_id: str, tags: list[str] | None = None) -> None:
    data: dict = {
        "id": dash_id, "title": "T", "scope": "personal",
        "tiles": [], "created_at": "", "updated_at": "",
        "theme": {"primary_color": "#1a4a8c", "font": "sans-serif", "logo_url": ""},
    }
    if tags is not None:
        data["tags"] = tags
    (tmp_path / f"{dash_id}.yaml").write_text(yaml.safe_dump(data))


# ── Unit test: tags round-trip through model ──────────────────────────────────

def test_tags_in_model(tmp_path):
    from app.dashboards.models import load_dashboard
    _write_yaml(tmp_path, "d-tags-model", tags=["emploi", "pilote"])
    d = load_dashboard(tmp_path / "d-tags-model.yaml")
    assert d.tags == ["emploi", "pilote"]


def test_tags_default_empty(tmp_path):
    from app.dashboards.models import load_dashboard
    _write_yaml(tmp_path, "d-tags-empty")
    d = load_dashboard(tmp_path / "d-tags-empty.yaml")
    assert d.tags == []


# ── Route tests ──────────────────────────────────────────────────────────────

def test_set_tags_ok(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    _write_yaml(tmp_path, "d-tags-1")
    r = client.put(
        "/dashboards/d-tags-1/tags",
        json={"tags": ["emploi", "pilote"]},
        headers=EDITOR,
    )
    assert r.status_code == 200
    assert r.json()["tags"] == ["emploi", "pilote"]
    # Persisted
    saved = yaml.safe_load((tmp_path / "d-tags-1.yaml").read_text())
    assert saved["tags"] == ["emploi", "pilote"]


def test_set_tags_clears(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    _write_yaml(tmp_path, "d-tags-2", tags=["a", "b"])
    r = client.put("/dashboards/d-tags-2/tags", json={"tags": []}, headers=EDITOR)
    assert r.status_code == 200
    assert r.json()["tags"] == []


def test_set_tags_requires_editor(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    _write_yaml(tmp_path, "d-tags-auth")
    r = client.put("/dashboards/d-tags-auth/tags", json={"tags": ["x"]}, headers=VIEWER)
    assert r.status_code == 403


def test_set_tags_too_many(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    _write_yaml(tmp_path, "d-tags-many")
    r = client.put(
        "/dashboards/d-tags-many/tags",
        json={"tags": [f"t{i}" for i in range(21)]},
        headers=EDITOR,
    )
    assert r.status_code == 422


def test_set_tags_not_found(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    r = client.put("/dashboards/no-such/tags", json={"tags": ["x"]}, headers=EDITOR)
    assert r.status_code == 404


def test_list_filtered_by_tag(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    monkeypatch.setattr("app.dashboards.favorites._FAVORITES_PATH", tmp_path / "favs.json")
    _write_yaml(tmp_path, "d-filter-1", tags=["emploi"])
    _write_yaml(tmp_path, "d-filter-2", tags=["population"])
    r = client.get("/dashboards?tag=emploi", headers=VIEWER)
    assert r.status_code == 200
    ids = [d["id"] for d in r.json()["dashboards"]]
    assert "d-filter-1" in ids
    assert "d-filter-2" not in ids

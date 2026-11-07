"""Tests for tile annotation (note) feature — PUT /dashboards/{id}/tiles/{id}/note."""
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


def _write_yaml(tmp_path: Path, dash_id: str, tile_note: str | None = None) -> None:
    tile: dict = {"id": "kpi1", "type": "kpi", "title": "Total", "sql_pinned": "SELECT 1 AS v"}
    if tile_note is not None:
        tile["note"] = tile_note
    data = {
        "id": dash_id, "title": "T", "scope": "personal",
        "tiles": [tile], "created_at": "", "updated_at": "",
        "theme": {"primary_color": "#1a4a8c", "font": "sans-serif", "logo_url": ""},
    }
    (tmp_path / f"{dash_id}.yaml").write_text(yaml.safe_dump(data))


# ── Unit test: note round-trips through model ───────────────────────────────

def test_tile_note_in_model(tmp_path):
    from app.dashboards.models import _tile_from_dict, Tile
    d = {"id": "t1", "type": "kpi", "title": "X", "note": "Source : INSTAD 2023"}
    tile = _tile_from_dict(d)
    assert tile.note == "Source : INSTAD 2023"


def test_tile_note_none_when_absent(tmp_path):
    from app.dashboards.models import _tile_from_dict
    d = {"id": "t1", "type": "kpi", "title": "X"}
    tile = _tile_from_dict(d)
    assert tile.note is None


# ── Route tests ──────────────────────────────────────────────────────────────

def test_set_note_ok(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    _write_yaml(tmp_path, "d-note-1")
    r = client.put(
        "/dashboards/d-note-1/tiles/kpi1/note",
        json={"note": "Source : INSTAD, Recensement 2023."},
        headers=EDITOR,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["note"] == "Source : INSTAD, Recensement 2023."
    assert data["tile_id"] == "kpi1"
    # Persisted in YAML
    saved = yaml.safe_load((tmp_path / "d-note-1.yaml").read_text())
    assert saved["tiles"][0]["note"] == "Source : INSTAD, Recensement 2023."


def test_set_note_clears_with_empty_string(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    _write_yaml(tmp_path, "d-note-2", tile_note="Old note")
    r = client.put(
        "/dashboards/d-note-2/tiles/kpi1/note",
        json={"note": ""},
        headers=EDITOR,
    )
    assert r.status_code == 200
    assert r.json()["note"] is None


def test_set_note_requires_editor(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    _write_yaml(tmp_path, "d-note-auth")
    r = client.put(
        "/dashboards/d-note-auth/tiles/kpi1/note",
        json={"note": "test"},
        headers=VIEWER,
    )
    assert r.status_code == 403


def test_set_note_dashboard_not_found(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    r = client.put(
        "/dashboards/no-such-dash/tiles/kpi1/note",
        json={"note": "x"},
        headers=EDITOR,
    )
    assert r.status_code == 404


def test_set_note_tile_not_found(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    _write_yaml(tmp_path, "d-note-5")
    r = client.put(
        "/dashboards/d-note-5/tiles/no-such-tile/note",
        json={"note": "x"},
        headers=EDITOR,
    )
    assert r.status_code == 404


def test_set_note_too_long(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    _write_yaml(tmp_path, "d-note-6")
    r = client.put(
        "/dashboards/d-note-6/tiles/kpi1/note",
        json={"note": "x" * 1001},
        headers=EDITOR,
    )
    assert r.status_code == 422

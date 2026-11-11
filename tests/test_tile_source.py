"""Tests for tile source attribution — PUT /dashboards/{id}/tiles/{id}/source."""
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


def _write_yaml(tmp_path: Path, dash_id: str, tile_source: str | None = None) -> None:
    tile: dict = {"id": "kpi1", "type": "kpi", "title": "Total", "sql_pinned": "SELECT 1 AS v"}
    if tile_source is not None:
        tile["source"] = tile_source
    data = {
        "id": dash_id, "title": "T", "scope": "personal",
        "tiles": [tile], "created_at": "", "updated_at": "",
        "theme": {"primary_color": "#1a4a8c", "font": "sans-serif", "logo_url": ""},
    }
    (tmp_path / f"{dash_id}.yaml").write_text(yaml.safe_dump(data))


# ── Unit tests ────────────────────────────────────────────────────────────────

def test_tile_source_in_model(tmp_path):
    from app.dashboards.models import _tile_from_dict
    d = {"id": "t1", "type": "kpi", "title": "X", "source": "INSTAD, Recensement 2023"}
    tile = _tile_from_dict(d)
    assert tile.source == "INSTAD, Recensement 2023"


def test_tile_source_none_when_absent(tmp_path):
    from app.dashboards.models import _tile_from_dict
    d = {"id": "t1", "type": "kpi", "title": "X"}
    tile = _tile_from_dict(d)
    assert tile.source is None


# ── Route tests ───────────────────────────────────────────────────────────────

def test_set_source_ok(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    _write_yaml(tmp_path, "d-src-1")
    r = client.put(
        "/dashboards/d-src-1/tiles/kpi1/source",
        json={"source": "BCD, Rapport Annuel 2024"},
        headers=EDITOR,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["source"] == "BCD, Rapport Annuel 2024"
    assert data["tile_id"] == "kpi1"
    saved = yaml.safe_load((tmp_path / "d-src-1.yaml").read_text())
    assert saved["tiles"][0]["source"] == "BCD, Rapport Annuel 2024"


def test_set_source_clears_with_empty_string(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    _write_yaml(tmp_path, "d-src-2", tile_source="Old source")
    r = client.put(
        "/dashboards/d-src-2/tiles/kpi1/source",
        json={"source": ""},
        headers=EDITOR,
    )
    assert r.status_code == 200
    assert r.json()["source"] is None


def test_set_source_requires_editor(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    _write_yaml(tmp_path, "d-src-auth")
    r = client.put(
        "/dashboards/d-src-auth/tiles/kpi1/source",
        json={"source": "test"},
        headers=VIEWER,
    )
    assert r.status_code == 403


def test_set_source_dashboard_not_found(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    r = client.put(
        "/dashboards/no-such-dash/tiles/kpi1/source",
        json={"source": "x"},
        headers=EDITOR,
    )
    assert r.status_code == 404


def test_set_source_tile_not_found(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    _write_yaml(tmp_path, "d-src-5")
    r = client.put(
        "/dashboards/d-src-5/tiles/no-such-tile/source",
        json={"source": "x"},
        headers=EDITOR,
    )
    assert r.status_code == 404


def test_set_source_too_long(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    _write_yaml(tmp_path, "d-src-6")
    r = client.put(
        "/dashboards/d-src-6/tiles/kpi1/source",
        json={"source": "x" * 301},
        headers=EDITOR,
    )
    assert r.status_code == 422


# ── Source in bulletin HTML ───────────────────────────────────────────────────

def test_bulletin_includes_source():
    from app.dashboards.models import Dashboard, DashboardTheme, Tile
    from app.dashboards.bulletin import generate_bulletin_html
    from unittest.mock import MagicMock

    tile = Tile(id="t1", type="table", title="Emploi", sql_pinned="SELECT 1 AS n",
                source="INSTAD, EDIM 2024")
    dash = Dashboard(id="d1", title="Test", scope="personal", tiles=[tile],
                     theme=DashboardTheme())

    store = MagicMock()
    store.execute.return_value = (["n"], [[1]])

    html = generate_bulletin_html(dash, store)
    # The CSS ::before pseudo-element adds "Source : "; the value appears directly in the tag
    assert "INSTAD, EDIM 2024" in html
    assert 'class="source-attr"' in html


def test_bulletin_no_source_block_when_absent():
    from app.dashboards.models import Dashboard, DashboardTheme, Tile
    from app.dashboards.bulletin import generate_bulletin_html
    from unittest.mock import MagicMock

    tile = Tile(id="t1", type="table", title="Emploi", sql_pinned="SELECT 1 AS n")
    dash = Dashboard(id="d1", title="Test", scope="personal", tiles=[tile],
                     theme=DashboardTheme())

    store = MagicMock()
    store.execute.return_value = (["n"], [[1]])

    html = generate_bulletin_html(dash, store)
    assert 'class="source-attr"' not in html


# ── Source in CSV export ──────────────────────────────────────────────────────

def test_csv_includes_source_header(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    _write_yaml(tmp_path, "d-src-csv", tile_source="StatCan, table 14-10-0287-01")
    r = client.get(
        "/dashboards/d-src-csv/tiles/kpi1/export/csv",
        headers=VIEWER,
    )
    assert r.status_code == 200
    text = r.content.decode("utf-8-sig")
    assert "Source : StatCan, table 14-10-0287-01" in text


def test_csv_no_source_comment_when_absent(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    _write_yaml(tmp_path, "d-src-csv-none")
    r = client.get(
        "/dashboards/d-src-csv-none/tiles/kpi1/export/csv",
        headers=VIEWER,
    )
    assert r.status_code == 200
    text = r.content.decode("utf-8-sig")
    assert "# Source" not in text

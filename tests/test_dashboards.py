"""Tests for dashboards models, renderer, templates, and API routes."""
import ast
import os
from dataclasses import asdict
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).parent.parent

# Keys are set by conftest.py before any import
_EDITOR_HEADERS = {"X-Api-Key": os.environ.get("SOVEREIGN_EDITOR_KEY", "test-editor-key-s6")}
_VIEWER_HEADERS = {"X-Api-Key": os.environ.get("SOVEREIGN_VIEWER_KEY", "test-viewer-key-s6")}


# ─── Models ──────────────────────────────────────────────────────────────────

from app.dashboards.models import (
    Dashboard,
    DashboardTemplate,
    DashboardTheme,
    Tile,
    load_dashboard,
    load_template,
    save_dashboard,
    save_template,
)


def _make_dashboard(dash_id: str = "test_dash") -> Dashboard:
    tiles = [
        Tile(id="t1", type="kpi", title="CA", metric="chiffre d'affaires"),
        Tile(id="t2", type="bar", title="Région", metric="chiffre d'affaires", dimensions=["region"]),
    ]
    return Dashboard(
        id=dash_id,
        title="Mon Dashboard",
        scope="personal",
        tiles=tiles,
        theme=DashboardTheme(primary_color="#ff0000"),
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
    )


def test_save_load_dashboard(tmp_path):
    d = _make_dashboard()
    p = tmp_path / "d.yaml"
    save_dashboard(d, p)
    d2 = load_dashboard(p)
    assert d2.id == d.id
    assert d2.title == d.title
    assert d2.scope == d.scope
    assert d2.theme.primary_color == "#ff0000"
    assert len(d2.tiles) == 2
    assert d2.tiles[0].id == "t1"
    assert d2.tiles[1].dimensions == ["region"]


def test_save_load_dashboard_roundtrip(tmp_path):
    d = _make_dashboard("rt")
    p = tmp_path / "rt.yaml"
    save_dashboard(d, p)
    d2 = load_dashboard(p)
    assert asdict(d) == asdict(d2)


def _make_template() -> DashboardTemplate:
    tiles = [
        Tile(id="k1", type="kpi", title="Total", metric="chiffre d'affaires"),
        Tile(id="b1", type="bar", title="Région", metric="chiffre d'affaires", dimensions=["region"]),
        Tile(id="b2", type="bar", title="Canal", metric="chiffre d'affaires", dimensions=["canal"]),
        Tile(id="k2", type="kpi", title="Panier", metric="panier moyen"),
    ]
    return DashboardTemplate(
        id="test_tmpl",
        title="Template Test",
        description="Un template de test",
        tiles=tiles,
    )


def test_save_load_template(tmp_path):
    t = _make_template()
    p = tmp_path / "tmpl.yaml"
    save_template(t, p)
    t2 = load_template(p)
    assert t2.id == t.id
    assert t2.description == t.description
    assert len(t2.tiles) == 4


def test_save_load_template_roundtrip(tmp_path):
    t = _make_template()
    p = tmp_path / "rt.yaml"
    save_template(t, p)
    t2 = load_template(p)
    assert asdict(t) == asdict(t2)


# ─── Renderer ────────────────────────────────────────────────────────────────

from app.dashboards.renderer import render_tile
from app.data.duckdb_store import DataStore


def _store_with_data() -> DataStore:
    store = DataStore()
    df = pd.DataFrame({"region": ["ON", "QC", "BC"], "montant_ht": [100.0, 200.0, 150.0]})
    store.load_dataframe("ventes", df)
    return store


def test_render_tile_with_sql():
    store = _store_with_data()
    tile = Tile(
        id="t1",
        type="bar",
        title="CA par région",
        sql_pinned="SELECT region, SUM(montant_ht) AS ca FROM ventes GROUP BY region",
    )
    result = render_tile(tile, store)
    assert result["error"] is None
    assert "region" in result["columns"]
    assert len(result["rows"]) == 3


def test_render_tile_blocked_by_sql_guard():
    store = _store_with_data()
    tile = Tile(
        id="bad",
        type="table",
        title="Attack",
        sql_pinned="DROP TABLE ventes",
    )
    result = render_tile(tile, store)
    assert result["error"] is not None
    assert result["columns"] == []
    assert result["rows"] == []


def test_render_tile_unknown_table():
    store = _store_with_data()
    tile = Tile(
        id="t_unk",
        type="table",
        title="Unknown",
        sql_pinned="SELECT * FROM does_not_exist",
    )
    result = render_tile(tile, store)
    assert result["error"] is not None


def test_render_metric_tile_no_sql():
    store = _store_with_data()
    tile = Tile(id="m1", type="kpi", title="CA", metric="chiffre d'affaires")
    result = render_tile(tile, store)
    assert result["error"] is not None
    assert "SQL" in result["error"]


def test_render_tile_insert_blocked():
    store = _store_with_data()
    tile = Tile(
        id="ins",
        type="table",
        title="Insert",
        sql_pinned="INSERT INTO ventes VALUES ('x', 0)",
    )
    result = render_tile(tile, store)
    assert result["error"] is not None


def test_render_tile_select_returns_data():
    store = _store_with_data()
    tile = Tile(
        id="all",
        type="table",
        title="All",
        sql_pinned="SELECT * FROM ventes",
    )
    result = render_tile(tile, store)
    assert result["error"] is None
    assert len(result["rows"]) == 3


# ─── sql_guard always called ──────────────────────────────────────────────────

def test_no_sql_guard_bypass_in_tile():
    """Verify render_tile source always imports validate_sql (static analysis)."""
    src = (ROOT / "app" / "dashboards" / "renderer.py").read_text()
    tree = ast.parse(src)
    # collect all names imported or called
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
    assert "validate_sql" in names, "render_tile must call validate_sql"


# ─── Templates on disk ────────────────────────────────────────────────────────

def test_three_templates_exist():
    tmpl_dir = ROOT / "templates"
    assert (tmpl_dir / "ventes.yaml").exists()
    assert (tmpl_dir / "finance.yaml").exists()
    assert (tmpl_dir / "operations.yaml").exists()


def test_templates_loadable():
    tmpl_dir = ROOT / "templates"
    for name in ["ventes.yaml", "finance.yaml", "operations.yaml"]:
        t = load_template(tmpl_dir / name)
        assert t.id
        assert t.title


def test_templates_have_four_tiles():
    tmpl_dir = ROOT / "templates"
    for name in ["ventes.yaml", "finance.yaml", "operations.yaml"]:
        t = load_template(tmpl_dir / name)
        assert len(t.tiles) == 4, f"{name} should have 4 tiles, got {len(t.tiles)}"


def test_templates_tiles_have_metric_no_sql():
    """Templates use metric, not sql_pinned (sql_pinned is for runtime pinning)."""
    tmpl_dir = ROOT / "templates"
    for name in ["ventes.yaml", "finance.yaml", "operations.yaml"]:
        t = load_template(tmpl_dir / name)
        for tile in t.tiles:
            assert tile.sql_pinned is None, f"{name}/{tile.id} should not have sql_pinned"
            assert tile.metric is not None, f"{name}/{tile.id} must have a metric"


# ─── Dashboard API ────────────────────────────────────────────────────────────

@pytest.fixture
def client(tmp_path, monkeypatch):
    """FastAPI test client with isolated data dir."""
    import app.routers.dashboards as dr
    monkeypatch.setattr(dr, "_DASHBOARDS_DIR", tmp_path / "dashboards")
    monkeypatch.setattr(dr, "_TEMPLATES_DIR", ROOT / "templates")
    from app.main import app
    return TestClient(app, headers=_EDITOR_HEADERS)


def test_list_dashboards_empty(client, tmp_path, monkeypatch):
    import app.routers.dashboards as dr
    monkeypatch.setattr(dr, "_DASHBOARDS_DIR", tmp_path / "empty_dbs")
    r = client.get("/dashboards")
    assert r.status_code == 200
    assert r.json()["dashboards"] == []


def test_create_and_get_dashboard(client):
    body = {
        "id": "dash_test",
        "title": "Test",
        "scope": "personal",
        "tiles": [{"id": "t1", "type": "kpi", "title": "CA", "metric": "chiffre d'affaires"}],
        "theme": {"primary_color": "#abc123"},
    }
    r = client.post("/dashboards", json=body)
    assert r.status_code == 200
    r2 = client.get("/dashboards/dash_test")
    assert r2.status_code == 200
    assert r2.json()["title"] == "Test"


def test_get_dashboard_not_found(client):
    r = client.get("/dashboards/no_such_dashboard")
    assert r.status_code == 404


def test_list_templates(client):
    r = client.get("/templates")
    assert r.status_code == 200
    tmpls = r.json()["templates"]
    ids = [t["id"] for t in tmpls]
    assert "ventes_v1" in ids
    assert "finance_v1" in ids
    assert "operations_v1" in ids


def test_get_template(client):
    # The file is named ventes.yaml, the router strips extension or searches by id
    r = client.get("/templates/ventes_v1")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == "ventes_v1"
    assert len(data["tiles"]) == 4


def test_get_template_not_found(client):
    r = client.get("/templates/nonexistent_xyz")
    assert r.status_code == 404


# ─── Sprint 26 : patch layout, add tile, remove tile ─────────────────────────

def _create_dash(client, dash_id: str = "s26_dash") -> None:
    body = {
        "id": dash_id,
        "title": "Sprint 26 Test",
        "scope": "personal",
        "tiles": [
            {"id": "t1", "type": "kpi", "title": "KPI 1"},
            {"id": "t2", "type": "bar", "title": "Bar 2"},
            {"id": "t3", "type": "line", "title": "Line 3"},
        ],
    }
    r = client.post("/dashboards", json=body)
    assert r.status_code == 200


def test_patch_layout_reorders_tiles(client):
    _create_dash(client)
    r = client.patch(
        "/dashboards/s26_dash/layout",
        json={"tiles": [{"id": "t3", "position": 0}, {"id": "t1", "position": 1}, {"id": "t2", "position": 2}]},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["order"] == ["t3", "t1", "t2"]


def test_patch_layout_returns_updated_at(client):
    _create_dash(client, "s26_ts")
    r = client.patch(
        "/dashboards/s26_ts/layout",
        json={"tiles": [{"id": "t1", "position": 0}, {"id": "t2", "position": 1}, {"id": "t3", "position": 2}]},
    )
    assert r.status_code == 200
    assert "updated_at" in r.json()


def test_patch_layout_missing_tile_400(client):
    _create_dash(client, "s26_miss")
    r = client.patch(
        "/dashboards/s26_miss/layout",
        json={"tiles": [{"id": "t1", "position": 0}, {"id": "t2", "position": 1}]},
    )
    assert r.status_code == 400


def test_patch_layout_extra_tile_400(client):
    _create_dash(client, "s26_extra")
    r = client.patch(
        "/dashboards/s26_extra/layout",
        json={"tiles": [
            {"id": "t1", "position": 0},
            {"id": "t2", "position": 1},
            {"id": "t3", "position": 2},
            {"id": "t_new", "position": 3},
        ]},
    )
    assert r.status_code == 400


def test_patch_layout_not_found(client):
    r = client.patch(
        "/dashboards/no_such/layout",
        json={"tiles": [{"id": "t1", "position": 0}]},
    )
    assert r.status_code == 404


def test_add_tile_appends(client):
    _create_dash(client, "s26_add")
    r = client.post(
        "/dashboards/s26_add/tiles",
        json={"id": "t_new", "type": "pie", "title": "Pie Chart"},
    )
    assert r.status_code == 200
    assert r.json()["tile_id"] == "t_new"
    # Verify tile is present in dashboard
    d = client.get("/dashboards/s26_add").json()
    tile_ids = [t["id"] for t in d["tiles"]]
    assert "t_new" in tile_ids


def test_add_tile_duplicate_409(client):
    _create_dash(client, "s26_dup")
    r = client.post(
        "/dashboards/s26_dup/tiles",
        json={"id": "t1", "type": "kpi", "title": "Duplicate"},
    )
    assert r.status_code == 409


def test_add_tile_missing_fields_400(client):
    _create_dash(client, "s26_flds")
    r = client.post(
        "/dashboards/s26_flds/tiles",
        json={"id": "t_only"},
    )
    assert r.status_code == 400


def test_add_tile_dashboard_not_found(client):
    r = client.post(
        "/dashboards/no_such/tiles",
        json={"id": "t1", "type": "kpi", "title": "X"},
    )
    assert r.status_code == 404


def test_remove_tile_success(client):
    _create_dash(client, "s26_rm")
    r = client.delete("/dashboards/s26_rm/tiles/t2")
    assert r.status_code == 200
    assert r.json()["tile_id"] == "t2"
    d = client.get("/dashboards/s26_rm").json()
    tile_ids = [t["id"] for t in d["tiles"]]
    assert "t2" not in tile_ids
    assert "t1" in tile_ids
    assert "t3" in tile_ids


def test_remove_tile_not_found_404(client):
    _create_dash(client, "s26_rm404")
    r = client.delete("/dashboards/s26_rm404/tiles/no_tile")
    assert r.status_code == 404


def test_remove_tile_dashboard_not_found(client):
    r = client.delete("/dashboards/no_such/tiles/t1")
    assert r.status_code == 404


def test_tile_position_persisted(client):
    """After patch_layout, get_dashboard returns tiles sorted by position."""
    _create_dash(client, "s26_pos")
    client.patch(
        "/dashboards/s26_pos/layout",
        json={"tiles": [{"id": "t3", "position": 0}, {"id": "t2", "position": 1}, {"id": "t1", "position": 2}]},
    )
    d = client.get("/dashboards/s26_pos").json()
    ids = [t["id"] for t in d["tiles"]]
    assert ids == ["t3", "t2", "t1"]

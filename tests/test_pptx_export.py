"""Tests for the PPTX export — generator unit tests + route."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("SOVEREIGN_EMBEDDER", "tfidf")

VIEWER = {"X-Api-Key": "test-viewer-key-s6"}


# ── Unit tests for pptx_export ────────────────────────────────────────────────

class _MockStore:
    def __init__(self, cols=None, rows=None):
        self._cols = cols or ["valeur"]
        self._rows = rows or [[42]]

    @property
    def tables(self):
        return []

    def execute(self, _sql):
        return self._cols, self._rows


def _make_dashboard(tmp_path: Path, dash_id: str, tiles: list | None = None):
    from app.dashboards.models import Dashboard, DashboardTheme, Tile
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    _tiles = tiles or [
        Tile(id="kpi1", type="kpi", title="PIB DJ", sql_pinned="SELECT 42 AS pib"),
        Tile(id="tab1", type="table", title="Régions",
             sql_pinned="SELECT 'Djibouti' AS region, 24.1 AS taux"),
        Tile(id="bar1", type="bar", title="Chômage",
             sql_pinned="SELECT 'Nord' AS zone, 33.2 AS val"),
    ]
    return Dashboard(
        id=dash_id,
        title="Test Export",
        scope="personal",
        tiles=_tiles,
        theme=DashboardTheme(primary_color="#1a4a8c"),
        created_at=now,
        updated_at=now,
    )


def test_generate_pptx_returns_bytes():
    from app.dashboards.pptx_export import generate_pptx
    store = _MockStore()
    d = _make_dashboard(Path("/tmp"), "test-pptx")
    result = generate_pptx(d, store)
    assert isinstance(result, bytes)
    assert len(result) > 1000  # real pptx is never empty


def test_generate_pptx_valid_zip():
    """PPTX is a ZIP archive — check magic bytes."""
    from app.dashboards.pptx_export import generate_pptx
    store = _MockStore()
    d = _make_dashboard(Path("/tmp"), "test-pptx-zip")
    result = generate_pptx(d, store)
    assert result[:2] == b"PK"  # ZIP/PPTX magic


def test_generate_pptx_slide_count():
    """Expect title slide + 1 slide per tile."""
    from app.dashboards.pptx_export import generate_pptx
    from pptx import Presentation
    import io
    store = _MockStore()
    d = _make_dashboard(Path("/tmp"), "test-pptx-slides")
    buf = generate_pptx(d, store)
    prs = Presentation(io.BytesIO(buf))
    assert len(prs.slides) == len(d.tiles) + 1  # +1 for title


def test_generate_pptx_custom_brand_color():
    from app.dashboards.pptx_export import _hex_to_rgb
    from pptx.dml.color import RGBColor
    assert _hex_to_rgb("#1a4a8c") == RGBColor(0x1A, 0x4A, 0x8C)


def test_generate_pptx_bad_color_fallback():
    from app.dashboards.pptx_export import _hex_to_rgb
    from pptx.dml.color import RGBColor
    r = _hex_to_rgb("not-a-color")
    assert r == RGBColor(0x1F, 0x77, 0xB4)


def test_generate_pptx_empty_store():
    """Store returning no rows should not crash."""
    from app.dashboards.pptx_export import generate_pptx
    store = _MockStore(cols=[], rows=[])
    d = _make_dashboard(Path("/tmp"), "test-pptx-empty")
    result = generate_pptx(d, store)
    assert isinstance(result, bytes)


def test_generate_pptx_table_tile():
    from app.dashboards.pptx_export import generate_pptx
    from pptx import Presentation
    import io
    from app.dashboards.models import Tile
    store = _MockStore(cols=["region", "taux"], rows=[("Djibouti", 24.1), ("Obock", 33.2)])
    d = _make_dashboard(Path("/tmp"), "test-pptx-table", tiles=[
        Tile(id="t1", type="table", title="Chômage par région",
             sql_pinned="SELECT region, taux FROM data"),
    ])
    buf = generate_pptx(d, store)
    prs = Presentation(io.BytesIO(buf))
    assert len(prs.slides) == 2  # title + 1 tile


# ── Route tests ───────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


def _write_yaml_dashboard(tmp_path: Path, dash_id: str) -> None:
    import yaml
    data = {
        "id": dash_id,
        "title": "Dashboard PPTX Test",
        "scope": "personal",
        "tiles": [
            {"id": "k1", "type": "kpi", "title": "KPI 1", "sql_pinned": "SELECT 1 AS v"},
        ],
        "theme": {"primary_color": "#1a4a8c", "font": "sans-serif", "logo_url": ""},
        "created_at": "", "updated_at": "",
    }
    (tmp_path / f"{dash_id}.yaml").write_text(yaml.safe_dump(data, allow_unicode=True))


def test_pptx_route_returns_binary(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    _write_yaml_dashboard(tmp_path, "d-pptx-1")
    r = client.get("/dashboards/d-pptx-1/export/pptx", headers=VIEWER)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.presentationml"
    )
    assert r.content[:2] == b"PK"


def test_pptx_route_missing_dashboard(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    r = client.get("/dashboards/ghost-pptx/export/pptx", headers=VIEWER)
    assert r.status_code == 404


def test_pptx_route_content_disposition(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    _write_yaml_dashboard(tmp_path, "d-pptx-2")
    r = client.get("/dashboards/d-pptx-2/export/pptx", headers=VIEWER)
    assert r.status_code == 200
    assert "d-pptx-2.pptx" in r.headers.get("content-disposition", "")


def test_pptx_route_requires_auth(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    _write_yaml_dashboard(tmp_path, "d-pptx-3")
    r = client.get("/dashboards/d-pptx-3/export/pptx")
    assert r.status_code == 401

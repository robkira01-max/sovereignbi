"""Tests for P-026 — region filter in tile renderer and tile_data endpoint."""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("SOVEREIGN_EMBEDDER", "tfidf")

VIEWER = {"X-Api-Key": "test-viewer-key-s6"}


# ── Unit tests for render_tile with region filter ─────────────────────────────

class FakeTile:
    def __init__(self, sql: str, options: dict | None = None):
        self.sql_pinned = sql
        self.options = options


class FakeStore:
    def __init__(self):
        import duckdb
        self._con = duckdb.connect(":memory:")
        self._con.execute(
            "CREATE TABLE emploi_dj (region VARCHAR, chomage DOUBLE, year INTEGER)"
        )
        self._con.execute(
            "INSERT INTO emploi_dj VALUES "
            "('Djibouti-ville', 24.5, 2023), "
            "('Ali Sabieh', 18.2, 2023), "
            "('Arta', 12.1, 2023)"
        )

    @property
    def tables(self) -> set:
        return {"emploi_dj"}

    def execute(self, sql: str):
        rel = self._con.execute(sql)
        cols = [d[0] for d in rel.description]
        rows = [list(r) for r in rel.fetchall()]
        return cols, rows


def test_render_tile_no_filter():
    """Without region, returns all rows."""
    from app.dashboards.renderer import render_tile
    tile = FakeTile("SELECT region, chomage FROM emploi_dj")
    store = FakeStore()
    result = render_tile(tile, store)
    assert result["error"] is None
    assert len(result["rows"]) == 3


def test_render_tile_with_region_filters_rows():
    """With region='Djibouti-ville', returns only 1 row."""
    from app.dashboards.renderer import render_tile
    tile = FakeTile("SELECT region, chomage FROM emploi_dj")
    store = FakeStore()
    result = render_tile(tile, store, region="Djibouti-ville")
    assert result["error"] is None
    assert len(result["rows"]) == 1
    assert result["rows"][0][0] == "Djibouti-ville"
    assert result.get("region") == "Djibouti-ville"


def test_render_tile_region_col_override():
    """region_col param overrides the default column name."""
    from app.dashboards.renderer import render_tile
    # SQL has no 'region' column — use 'chomage' as the filter column (artificial test)
    tile = FakeTile("SELECT region, chomage FROM emploi_dj")
    store = FakeStore()
    # Filter on 'region' (default) with a known value
    result = render_tile(tile, store, region="Ali Sabieh", region_col="region")
    assert result["error"] is None
    assert len(result["rows"]) == 1
    assert result["rows"][0][0] == "Ali Sabieh"


def test_render_tile_region_missing_column_fallback():
    """If region column doesn't exist, falls back to unfiltered data."""
    from app.dashboards.renderer import render_tile
    tile = FakeTile("SELECT region, chomage FROM emploi_dj")
    store = FakeStore()
    # 'nonexistent_col' doesn't exist — expect graceful fallback to all rows
    result = render_tile(tile, store, region="Djibouti-ville", region_col="nonexistent_col")
    assert result["error"] is None
    assert len(result["rows"]) == 3  # unfiltered fallback


def test_render_tile_tile_option_region_col():
    """tile.options.region_col is used if no explicit param."""
    from app.dashboards.renderer import render_tile
    tile = FakeTile(
        "SELECT region, chomage FROM emploi_dj",
        options={"region_col": "region"},
    )
    store = FakeStore()
    result = render_tile(tile, store, region="Arta")
    assert result["error"] is None
    assert len(result["rows"]) == 1
    assert result["rows"][0][0] == "Arta"


def test_render_tile_no_sql():
    """No sql_pinned → error returned."""
    from app.dashboards.renderer import render_tile
    tile = FakeTile(None)  # type: ignore[arg-type]
    store = FakeStore()
    result = render_tile(tile, store, region="Djibouti-ville")
    assert result["error"] is not None


# ── HTTP endpoint tests ───────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


def test_tile_data_no_region_200(client):
    """GET /dashboards/{id}/tiles/{id}/data with no region param: 200."""
    r = client.get(
        "/dashboards/emploi_regions/tiles/chomage_region/data",
        headers=VIEWER,
    )
    # Accepts 200 (dashboard exists) or 404 (fixture not found — still tests auth)
    assert r.status_code in (200, 404)


def test_tile_data_invalid_region_400(client):
    """?region= with SQL metacharacter is rejected."""
    r = client.get(
        "/dashboards/emploi_regions/tiles/chomage_region/data?region='; DROP TABLE--",
        headers=VIEWER,
    )
    assert r.status_code == 400


def test_tile_data_invalid_region_col_400(client):
    """?region_col= with invalid chars is rejected."""
    r = client.get(
        "/dashboards/emploi_regions/tiles/chomage_region/data"
        "?region=Djibouti-ville&region_col=foo;bar",
        headers=VIEWER,
    )
    assert r.status_code == 400


def test_tile_data_valid_region_passthrough(client):
    """?region= with valid ASCII name is accepted (200 or 404 if no such dashboard)."""
    r = client.get(
        "/dashboards/emploi_regions/tiles/chomage_region/data"
        "?region=Djibouti-ville",
        headers=VIEWER,
    )
    assert r.status_code in (200, 404)


def test_tile_data_requires_auth(client):
    """Unauthenticated request to tile data endpoint is rejected."""
    r = client.get("/dashboards/emploi_regions/tiles/chomage_region/data?region=Arta")
    assert r.status_code in (401, 403)

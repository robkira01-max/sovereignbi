"""Tests for HeatmapTile — dashboard YAML round-trip (pure-model, no HTTP)."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

os.environ.setdefault("SOVEREIGN_EMBEDDER", "tfidf")


def test_heatmap_tile_yaml_roundtrip():
    from app.dashboards.models import Tile, Dashboard, DashboardTheme, save_dashboard, load_dashboard
    with tempfile.TemporaryDirectory() as d:
        tile = Tile(
            id="h1", type="heatmap", title="Exportations",
            sql_pinned="SELECT m, v FROM t LIMIT 100",
            options={"colorScheme": "orange", "showValues": True},
        )
        db = Dashboard(
            id="heatmap_rt", title="HeatmapRT", scope="test",
            tiles=[tile], theme=DashboardTheme(),
        )
        p = Path(d) / "heatmap_rt.yaml"
        save_dashboard(db, p)
        loaded = load_dashboard(p)
        assert loaded.tiles[0].type == "heatmap"
        assert loaded.tiles[0].options["colorScheme"] == "orange"
        assert loaded.tiles[0].options["showValues"] is True


def test_heatmap_tile_type_persists():
    from app.dashboards.models import Tile, Dashboard, DashboardTheme, save_dashboard, load_dashboard
    with tempfile.TemporaryDirectory() as d:
        tile = Tile(id="h2", type="heatmap", title="Flux 2D",
                    sql_pinned="SELECT h, v, r FROM t LIMIT 100", options={})
        db = Dashboard(id="hm2", title="HM2", scope="test",
                       tiles=[tile], theme=DashboardTheme())
        p = Path(d) / "hm2.yaml"
        save_dashboard(db, p)
        loaded = load_dashboard(p)
        assert loaded.tiles[0].type == "heatmap"


def test_heatmap_tile_options_roundtrip():
    from app.dashboards.models import Tile, Dashboard, DashboardTheme, save_dashboard, load_dashboard
    with tempfile.TemporaryDirectory() as d:
        opts = {"colorScheme": "green", "showValues": False}
        tile = Tile(id="h3", type="heatmap", title="Green",
                    sql_pinned="SELECT x, y FROM t LIMIT 10", options=opts)
        db = Dashboard(id="hm3", title="HM3", scope="test",
                       tiles=[tile], theme=DashboardTheme())
        p = Path(d) / "hm3.yaml"
        save_dashboard(db, p)
        loaded = load_dashboard(p)
        assert loaded.tiles[0].options == opts

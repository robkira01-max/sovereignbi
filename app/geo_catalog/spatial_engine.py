"""DuckDB Spatial analysis engine — P-023."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import duckdb

from app.geo_catalog.registry import get_layer, load_catalog

_PROJECT_ROOT = Path(__file__).parent.parent.parent

# Allowlist: file_path in catalog must be under project root (no traversal)
def _safe_path(relative: str) -> Path:
    p = (_PROJECT_ROOT / relative).resolve()
    if not str(p).startswith(str(_PROJECT_ROOT)):
        raise ValueError(f"file_path outside project root: {relative!r}")
    if not p.exists():
        raise FileNotFoundError(f"Layer file not found: {p}")
    return p


def _safe_table_name(layer_id: str) -> str:
    """Convert layer_id to a safe DuckDB table name."""
    return re.sub(r"[^a-zA-Z0-9_]", "_", layer_id)


SUPPORTED_ANALYSES = {
    "area":     "Area in km² of each polygon feature (ST_Area_Spheroid).",
    "centroid": "Centroid coordinates (lon, lat) of each feature.",
    "bbox":     "Bounding box (min_lon, min_lat, max_lon, max_lat) of each feature.",
    "nearest":  "Feature(s) nearest to a query point (lon, lat). Requires params: lon, lat, limit=5.",
    "summary":  "Layer summary: feature count, total area km², geographic extent.",
}


class SpatialEngine:
    """Per-request DuckDB connection with spatial extension loaded."""

    def __init__(self) -> None:
        self._con = duckdb.connect()
        self._con.execute("LOAD spatial;")
        self._loaded: set[str] = set()

    def _load_layer(self, layer_id: str) -> tuple[str, str]:
        """Load layer into DuckDB if not already loaded. Returns (table_name, name_column)."""
        layer = get_layer(layer_id)
        if layer is None:
            raise ValueError(f"Unknown layer: {layer_id!r}")
        if not layer.file_path:
            raise ValueError(f"Layer {layer_id!r} has no file_path in catalog")
        path = _safe_path(layer.file_path)
        tname = _safe_table_name(layer_id)
        if layer_id not in self._loaded:
            self._con.execute(
                f"CREATE TABLE {tname} AS SELECT * FROM ST_Read('{path}')"
            )
            self._loaded.add(layer_id)
        return tname, layer.name_column

    def analyze(self, layer_id: str, analysis: str, params: dict[str, Any]) -> list[dict]:
        if analysis not in SUPPORTED_ANALYSES:
            raise ValueError(
                f"Unsupported analysis {analysis!r}. "
                f"Supported: {list(SUPPORTED_ANALYSES)}"
            )
        tname, name_col = self._load_layer(layer_id)
        dispatch = {
            "area":     self._area,
            "centroid": self._centroid,
            "bbox":     self._bbox,
            "nearest":  self._nearest,
            "summary":  self._summary,
        }
        return dispatch[analysis](tname, name_col, params)

    def _area(self, tname: str, name_col: str, _params: dict) -> list[dict]:
        rows = self._con.execute(f"""
            SELECT {name_col} AS name,
                   ROUND(ST_Area_Spheroid(geom) / 1e6, 2) AS area_km2
            FROM {tname}
            ORDER BY area_km2 DESC
        """).fetchall()
        return [{"name": r[0], "area_km2": r[1]} for r in rows]

    def _centroid(self, tname: str, name_col: str, _params: dict) -> list[dict]:
        rows = self._con.execute(f"""
            SELECT {name_col} AS name,
                   ROUND(ST_X(ST_Centroid(geom)), 6) AS lon,
                   ROUND(ST_Y(ST_Centroid(geom)), 6) AS lat
            FROM {tname}
            ORDER BY name
        """).fetchall()
        return [{"name": r[0], "lon": r[1], "lat": r[2]} for r in rows]

    def _bbox(self, tname: str, name_col: str, _params: dict) -> list[dict]:
        rows = self._con.execute(f"""
            SELECT {name_col} AS name,
                   ROUND(ST_XMin(geom), 6) AS min_lon,
                   ROUND(ST_YMin(geom), 6) AS min_lat,
                   ROUND(ST_XMax(geom), 6) AS max_lon,
                   ROUND(ST_YMax(geom), 6) AS max_lat
            FROM {tname}
            ORDER BY name
        """).fetchall()
        return [
            {"name": r[0], "min_lon": r[1], "min_lat": r[2], "max_lon": r[3], "max_lat": r[4]}
            for r in rows
        ]

    def _nearest(self, tname: str, name_col: str, params: dict) -> list[dict]:
        try:
            lon = float(params["lon"])
            lat = float(params["lat"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("nearest requires params: lon (float), lat (float)") from exc
        limit = min(int(params.get("limit", 5)), 20)
        rows = self._con.execute(f"""
            SELECT {name_col} AS name,
                   ROUND(ST_Distance(geom, ST_GeomFromText('POINT({lon} {lat})')) * 111320, 0) AS dist_m
            FROM {tname}
            ORDER BY dist_m
            LIMIT {limit}
        """).fetchall()
        return [{"name": r[0], "dist_m": r[1]} for r in rows]

    def _summary(self, tname: str, name_col: str, _params: dict) -> list[dict]:
        row = self._con.execute(f"""
            SELECT
                COUNT(*) AS feature_count,
                ROUND(SUM(ST_Area_Spheroid(geom)) / 1e6, 1) AS total_area_km2,
                ROUND(MIN(ST_XMin(geom)), 4) AS min_lon,
                ROUND(MIN(ST_YMin(geom)), 4) AS min_lat,
                ROUND(MAX(ST_XMax(geom)), 4) AS max_lon,
                ROUND(MAX(ST_YMax(geom)), 4) AS max_lat
            FROM {tname}
        """).fetchone()
        return [{
            "feature_count": row[0],
            "total_area_km2": row[1],
            "extent": {
                "min_lon": row[2], "min_lat": row[3],
                "max_lon": row[4], "max_lat": row[5],
            },
        }]

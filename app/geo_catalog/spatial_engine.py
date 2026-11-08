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
    "area":         "Area in km² of each polygon feature (ST_Area_Spheroid).",
    "centroid":     "Centroid coordinates (lon, lat) of each feature.",
    "bbox":         "Bounding box (min_lon, min_lat, max_lon, max_lat) of each feature.",
    "nearest":      "Feature(s) nearest to a query point. Requires params: lon, lat, limit=5.",
    "summary":      "Layer summary: feature count, total area km², geographic extent.",
    # P-025
    "buffer":       "Features within radius_km of a reference point. Params: lon, lat, radius_km, limit=50.",
    "intersection": "Features from this layer that intersect features from another layer. Params: layer_id_b.",
    "density":      "Value-per-area for each polygon. Params: value_col (numeric column, e.g. pop_estimated).",
}

_SAFE_COL_RE = re.compile(r"^[a-zA-Z0-9_]+$")


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

    def analyze(
        self,
        layer_id: str,
        analysis: str,
        params: dict[str, Any],
        layer_id_b: str | None = None,
    ) -> list[dict]:
        if analysis not in SUPPORTED_ANALYSES:
            raise ValueError(
                f"Unsupported analysis {analysis!r}. "
                f"Supported: {list(SUPPORTED_ANALYSES)}"
            )
        tname, name_col = self._load_layer(layer_id)
        dispatch = {
            "area":         self._area,
            "centroid":     self._centroid,
            "bbox":         self._bbox,
            "nearest":      self._nearest,
            "summary":      self._summary,
            "buffer":       self._buffer,
            "density":      self._density,
            "intersection": lambda t, n, p: self._intersection(t, n, p, layer_id_b),
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

    # ── P-025 ────────────────────────────────────────────────────────────────

    def _buffer(self, tname: str, name_col: str, params: dict) -> list[dict]:
        """Features whose geometry is within radius_km of a reference point."""
        try:
            lon = float(params["lon"])
            lat = float(params["lat"])
            radius_km = float(params["radius_km"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("buffer requires params: lon (float), lat (float), radius_km (float)") from exc
        limit = min(int(params.get("limit", 50)), 200)
        radius_m = radius_km * 1000
        rows = self._con.execute(f"""
            SELECT {name_col} AS name,
                   ROUND(ST_Distance(geom, ST_GeomFromText('POINT({lon} {lat})')) * 111320, 0) AS dist_m
            FROM {tname}
            WHERE ST_Distance(geom, ST_GeomFromText('POINT({lon} {lat})')) * 111320 <= {radius_m}
            ORDER BY dist_m
            LIMIT {limit}
        """).fetchall()
        return [{"name": r[0], "dist_m": r[1]} for r in rows]

    def _intersection(
        self, tname_a: str, name_col_a: str, _params: dict, layer_id_b: str | None
    ) -> list[dict]:
        """Feature pairs that intersect between two layers, with overlap area."""
        if not layer_id_b:
            raise ValueError("intersection requires layer_id_b (second layer identifier)")
        tname_b, name_col_b = self._load_layer(layer_id_b)
        rows = self._con.execute(f"""
            SELECT a.{name_col_a} AS feature_a,
                   b.{name_col_b} AS feature_b,
                   ROUND(ST_Area_Spheroid(ST_Intersection(a.geom, b.geom)) / 1e6, 4) AS overlap_km2
            FROM {tname_a} a
            JOIN {tname_b} b ON ST_Intersects(a.geom, b.geom)
            ORDER BY overlap_km2 DESC
            LIMIT 200
        """).fetchall()
        return [{"feature_a": r[0], "feature_b": r[1], "overlap_km2": r[2]} for r in rows]

    def _density(self, tname: str, name_col: str, params: dict) -> list[dict]:
        """Value-per-area density for each polygon feature."""
        value_col = params.get("value_col", "")
        if value_col:
            if not _SAFE_COL_RE.match(value_col):
                raise ValueError(f"value_col contains invalid characters: {value_col!r}")
            rows = self._con.execute(f"""
                SELECT {name_col} AS name,
                       CAST({value_col} AS DOUBLE) AS value,
                       ROUND(ST_Area_Spheroid(geom) / 1e6, 2) AS area_km2,
                       ROUND(CAST({value_col} AS DOUBLE) / (ST_Area_Spheroid(geom) / 1e6), 4) AS density_per_km2
                FROM {tname}
                WHERE {value_col} IS NOT NULL
                ORDER BY density_per_km2 DESC
            """).fetchall()
            return [
                {"name": r[0], "value": r[1], "area_km2": r[2], "density_per_km2": r[3]}
                for r in rows
            ]
        # No value_col: return area distribution (smallest first → highest base density)
        rows = self._con.execute(f"""
            SELECT {name_col} AS name,
                   ROUND(ST_Area_Spheroid(geom) / 1e6, 2) AS area_km2,
                   ROUND(1.0 / (ST_Area_Spheroid(geom) / 1e6), 6) AS inv_area_per_km2
            FROM {tname}
            ORDER BY area_km2 ASC
        """).fetchall()
        return [{"name": r[0], "area_km2": r[1], "inv_area_per_km2": r[2]} for r in rows]

"""GeoJSON / GeoPackage / GeoParquet import pipeline — P-024."""
from __future__ import annotations

import re
import tempfile
import time
from pathlib import Path

import duckdb
import yaml

_PROJECT_ROOT = Path(__file__).parent.parent.parent
_IMPORTS_DIR  = _PROJECT_ROOT / "data" / "geo" / "imports"
_CATALOG_PATH = _PROJECT_ROOT / "data" / "geo" / "catalog.yaml"

ALLOWED_EXTENSIONS = {".geojson", ".json", ".gpkg", ".parquet"}
MAX_BYTES = 50 * 1024 * 1024  # 50 MB

_NAME_CANDIDATES = ["name", "nom", "label", "title", "libelle", "shapename"]


def _safe_stem(filename: str) -> str:
    """Extract safe alphanumeric stem from filename."""
    stem = Path(filename).stem
    return re.sub(r"[^a-zA-Z0-9_]", "_", stem).lower()[:40]


def _detect_name_col(columns: list[str]) -> str:
    lower = [c.lower() for c in columns]
    for cand in _NAME_CANDIDATES:
        if cand in lower:
            return columns[lower.index(cand)]
    # Fall back to first non-geometry column
    non_geom = [c for c in columns if c.lower() not in ("geom", "geometry", "ogc_fid")]
    return non_geom[0] if non_geom else columns[0]


def _validate_with_duckdb(path: Path) -> dict:
    """Load file into DuckDB Spatial and extract metadata. Raises ValueError on bad data."""
    con = duckdb.connect()
    con.execute("LOAD spatial;")
    try:
        con.execute(f"CREATE TABLE _import_tmp AS SELECT * FROM ST_Read('{path}')")
    except Exception as exc:
        raise ValueError(f"Cannot read geographic file: {exc}") from exc

    cols = [c[0] for c in con.execute("DESCRIBE _import_tmp").fetchall()]
    if "geom" not in cols:
        raise ValueError("File has no geometry column — not a valid geographic dataset")

    count = con.execute("SELECT COUNT(*) FROM _import_tmp").fetchone()[0]
    if count == 0:
        raise ValueError("File contains no features")

    gtype = con.execute("SELECT ST_GeometryType(geom) FROM _import_tmp LIMIT 1").fetchone()[0]
    bbox  = con.execute(
        "SELECT MIN(ST_XMin(geom)), MIN(ST_YMin(geom)), MAX(ST_XMax(geom)), MAX(ST_YMax(geom)) FROM _import_tmp"
    ).fetchone()

    prop_cols = [c for c in cols if c.lower() not in ("geom", "geometry", "ogc_fid")]
    name_col  = _detect_name_col(prop_cols) if prop_cols else "OGC_FID"
    return {
        "feature_count": count,
        "geometry_type": gtype or "Unknown",
        "bbox": {"min_lon": bbox[0], "min_lat": bbox[1], "max_lon": bbox[2], "max_lat": bbox[3]},
        "columns": cols,
        "name_column": name_col,
    }


def _append_to_catalog(layer_dict: dict) -> None:
    """Append a new layer entry to catalog.yaml and invalidate registry cache."""
    raw = yaml.safe_load(_CATALOG_PATH.read_text(encoding="utf-8"))
    raw.setdefault("layers", []).append(layer_dict)
    _CATALOG_PATH.write_text(
        yaml.safe_dump(raw, allow_unicode=True, default_flow_style=False),
        encoding="utf-8",
    )
    # Invalidate the in-memory catalog cache
    from app.geo_catalog.registry import _load_catalog_cached
    _load_catalog_cached.cache_clear()


def import_layer(
    filename: str,
    content: bytes,
    name_fr: str,
    name_en: str = "",
    description_fr: str = "",
    description_en: str = "",
    source: str = "Import utilisateur",
    license: str = "À vérifier",
    license_url: str = "",
    coverage: str = "",
    catalog_path: Path | None = None,
) -> dict:
    """
    Validate and store a geographic file, register it in catalog.yaml.
    Returns the new layer dict (as stored in YAML).
    Raises ValueError for validation errors, OSError for I/O errors.
    """
    # 1. Extension check
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type {suffix!r}. "
            f"Allowed: {sorted(ALLOWED_EXTENSIONS)}"
        )

    # 2. Size check
    if len(content) > MAX_BYTES:
        mb = len(content) / (1024 * 1024)
        raise ValueError(f"File too large ({mb:.1f} MB). Max: {MAX_BYTES // (1024*1024)} MB")

    # 3. Write to temp file for DuckDB validation
    _IMPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        suffix=suffix, dir=_IMPORTS_DIR, delete=False
    ) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        # 4. Validate + extract metadata
        meta = _validate_with_duckdb(tmp_path)

        # 5. Move to permanent path with safe name
        stem   = _safe_stem(filename)
        ts     = str(int(time.time()))[-6:]
        safe_name = f"{stem}_{ts}{suffix}"
        dest   = _IMPORTS_DIR / safe_name
        tmp_path.rename(dest)
        tmp_path = dest   # update reference so error handler doesn't try to delete twice

        # 6. Build path relative to project root when possible, absolute otherwise (tests)
        try:
            rel_path = str(dest.relative_to(_PROJECT_ROOT))
        except ValueError:
            rel_path = str(dest)

        # 7. Build layer dict
        layer_id = f"import_{stem}_{ts}"
        layer_dict: dict = {
            "id":             layer_id,
            "name_fr":        name_fr or stem,
            "name_en":        name_en or name_fr or stem,
            "description_fr": description_fr,
            "description_en": description_en,
            "format":         suffix.lstrip("."),
            "geometry_type":  meta["geometry_type"],
            "source":         source,
            "license":        license,
            "license_url":    license_url,
            "date_acquired":  time.strftime("%Y-%m-%d"),
            "coverage":       coverage,
            "feature_count":  meta["feature_count"],
            "status":         "draft",
            "warnings":       [{
                "fr": "Couche importée — statut à valider avant usage institutionnel.",
                "en": "Imported layer — status must be validated before institutional use.",
            }],
            "api_endpoint":   f"/api/v1/geo/dj/{layer_id}",
            "file_path":      rel_path,
            "name_column":    meta["name_column"],
            "enabled":        False,
        }

        # 8. Register in catalog
        cat_path = catalog_path or _CATALOG_PATH
        raw = yaml.safe_load(cat_path.read_text(encoding="utf-8"))
        raw.setdefault("layers", []).append(layer_dict)
        cat_path.write_text(
            yaml.safe_dump(raw, allow_unicode=True, default_flow_style=False),
            encoding="utf-8",
        )
        from app.geo_catalog.registry import _load_catalog_cached
        _load_catalog_cached.cache_clear()

        return layer_dict

    except Exception:
        # Clean up temp/permanent file on any error
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise

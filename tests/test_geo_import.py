"""P-024 — Tests import géographique (GeoJSON / GeoPackage / GeoParquet)."""
from __future__ import annotations

import io
import json
import shutil
import tempfile
from pathlib import Path

import pytest
import yaml

from app.geo_catalog.importer import (
    ALLOWED_EXTENSIONS,
    MAX_BYTES,
    _detect_name_col,
    _safe_stem,
    _validate_with_duckdb,
    import_layer,
)


# ---------------------------------------------------------------------------
# Isolate HTTP tests: redirect catalog + imports dir to a temp location
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _isolate_importer(tmp_path, monkeypatch):
    """
    For every test in this module, patch the importer so HTTP route tests
    write to a temp catalog/imports dir instead of the real one.
    """
    import app.geo_catalog.importer as mod
    import app.geo_catalog.registry as reg

    # Create isolated catalog + imports dir
    cat = tmp_path / "catalog.yaml"
    cat.write_text(yaml.safe_dump({"version": "1", "layers": []}))
    imp_dir = tmp_path / "imports"
    imp_dir.mkdir()

    monkeypatch.setattr(mod, "_CATALOG_PATH", cat)
    monkeypatch.setattr(mod, "_IMPORTS_DIR", imp_dir)
    # Also clear the registry LRU cache so it re-reads the temp catalog
    reg._load_catalog_cached.cache_clear()
    yield
    reg._load_catalog_cached.cache_clear()

# ---------------------------------------------------------------------------
# Minimal valid GeoJSON for tests
# ---------------------------------------------------------------------------

_GEOJSON = json.dumps({
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [[[43.0, 11.5], [43.1, 11.5], [43.1, 11.6], [43.0, 11.6], [43.0, 11.5]]]},
            "properties": {"name": "Zone Test", "code": "ZT"},
        },
        {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [[[43.2, 11.7], [43.3, 11.7], [43.3, 11.8], [43.2, 11.8], [43.2, 11.7]]]},
            "properties": {"name": "Zone B", "code": "ZB"},
        },
    ],
})

_GEOJSON_BYTES = _GEOJSON.encode()


# ---------------------------------------------------------------------------
# Unit tests — helpers
# ---------------------------------------------------------------------------

def test_safe_stem_basic():
    assert _safe_stem("my layer.geojson") == "my_layer"


def test_safe_stem_path_injection():
    # Path traversal attempt — only the stem is kept
    stem = _safe_stem("../../etc/passwd.geojson")
    assert ".." not in stem
    assert "/" not in stem


def test_safe_stem_max_length():
    long_name = "a" * 100 + ".geojson"
    assert len(_safe_stem(long_name)) <= 40


def test_detect_name_col_name():
    assert _detect_name_col(["code", "name", "geom"]) == "name"


def test_detect_name_col_fallback():
    # No known candidate — first non-geom column
    assert _detect_name_col(["OGC_FID", "geom", "region_code"]) == "region_code"


def test_allowed_extensions():
    assert ".geojson" in ALLOWED_EXTENSIONS
    assert ".gpkg" in ALLOWED_EXTENSIONS
    assert ".parquet" in ALLOWED_EXTENSIONS
    assert ".json" in ALLOWED_EXTENSIONS
    assert ".shp" not in ALLOWED_EXTENSIONS


def test_max_bytes():
    assert MAX_BYTES == 50 * 1024 * 1024


# ---------------------------------------------------------------------------
# Unit tests — _validate_with_duckdb
# ---------------------------------------------------------------------------

def test_validate_valid_geojson(tmp_path):
    p = tmp_path / "test.geojson"
    p.write_bytes(_GEOJSON_BYTES)
    meta = _validate_with_duckdb(p)
    assert meta["feature_count"] == 2
    assert meta["geometry_type"] == "POLYGON"
    assert meta["name_column"] == "name"
    assert meta["bbox"]["min_lon"] == pytest.approx(43.0, abs=0.1)


def test_validate_bad_file(tmp_path):
    p = tmp_path / "bad.geojson"
    p.write_text("not valid json at all {{{")
    with pytest.raises(ValueError, match="Cannot read"):
        _validate_with_duckdb(p)


# ---------------------------------------------------------------------------
# Unit tests — import_layer
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_catalog(tmp_path):
    """Create a minimal catalog.yaml and imports dir for isolated tests."""
    cat = tmp_path / "catalog.yaml"
    cat.write_text(yaml.safe_dump({"version": "1", "layers": []}))
    imp_dir = tmp_path / "data" / "geo" / "imports"
    imp_dir.mkdir(parents=True)

    # Monkey-patch _IMPORTS_DIR inside importer module
    import app.geo_catalog.importer as mod
    orig_dir = mod._IMPORTS_DIR
    mod._IMPORTS_DIR = imp_dir
    yield cat, imp_dir
    mod._IMPORTS_DIR = orig_dir


def test_import_valid_geojson(tmp_catalog):
    cat_path, imp_dir = tmp_catalog
    layer = import_layer(
        filename="test_zone.geojson",
        content=_GEOJSON_BYTES,
        name_fr="Zone de test",
        name_en="Test zone",
        catalog_path=cat_path,
    )
    assert layer["id"].startswith("import_test_zone_")
    assert layer["feature_count"] == 2
    assert layer["status"] == "draft"
    assert layer["enabled"] is False
    assert layer["geometry_type"] == "POLYGON"
    assert layer["name_column"] == "name"
    assert layer["format"] == "geojson"
    # File must be on disk
    assert Path(layer["file_path"]).is_file() or (imp_dir / Path(layer["file_path"]).name).exists()


def test_import_registers_in_catalog(tmp_catalog):
    cat_path, _ = tmp_catalog
    import_layer("zone.geojson", _GEOJSON_BYTES, "Zone", catalog_path=cat_path)
    raw = yaml.safe_load(cat_path.read_text())
    assert len(raw["layers"]) == 1
    assert raw["layers"][0]["status"] == "draft"


def test_import_multiple_appends(tmp_catalog):
    cat_path, _ = tmp_catalog
    import_layer("a.geojson", _GEOJSON_BYTES, "A", catalog_path=cat_path)
    import_layer("b.geojson", _GEOJSON_BYTES, "B", catalog_path=cat_path)
    raw = yaml.safe_load(cat_path.read_text())
    assert len(raw["layers"]) == 2


def test_import_bad_extension(tmp_catalog):
    cat_path, _ = tmp_catalog
    with pytest.raises(ValueError, match="Unsupported file type"):
        import_layer("file.shp", b"...", "Test", catalog_path=cat_path)


def test_import_oversized(tmp_catalog):
    cat_path, _ = tmp_catalog
    big = b"x" * (MAX_BYTES + 1)
    with pytest.raises(ValueError, match="too large"):
        import_layer("big.geojson", big, "Big", catalog_path=cat_path)


def test_import_invalid_geodata(tmp_catalog):
    cat_path, _ = tmp_catalog
    with pytest.raises(ValueError, match="Cannot read"):
        import_layer("bad.geojson", b"not geojson", "Bad", catalog_path=cat_path)


def test_import_has_draft_warning(tmp_catalog):
    cat_path, _ = tmp_catalog
    layer = import_layer("z.geojson", _GEOJSON_BYTES, "Z", catalog_path=cat_path)
    assert len(layer["warnings"]) >= 1
    assert any("import" in w.get("fr", "").lower() for w in layer["warnings"])


# ---------------------------------------------------------------------------
# HTTP tests
# ---------------------------------------------------------------------------

VIEWER = "test-viewer-key-s6"
EDITOR = "test-editor-key-s6"


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


def _geojson_upload(client, api_key: str, filename: str = "zone.geojson", content: bytes = _GEOJSON_BYTES, name_fr: str = "Zone Test"):
    return client.post(
        "/api/v1/geo/import",
        headers={"X-Api-Key": api_key},
        files={"file": (filename, io.BytesIO(content), "application/geo+json")},
        data={"name_fr": name_fr},
    )


def test_import_auth_required(client):
    r = client.post(
        "/api/v1/geo/import",
        files={"file": ("z.geojson", io.BytesIO(_GEOJSON_BYTES), "application/geo+json")},
        data={"name_fr": "Z"},
    )
    assert r.status_code == 401


def test_import_viewer_forbidden(client):
    r = _geojson_upload(client, VIEWER)
    assert r.status_code == 403


def test_import_valid_geojson_http(client):
    r = _geojson_upload(client, EDITOR)
    assert r.status_code == 201, r.text
    body = r.json()
    assert "layer" in body
    layer = body["layer"]
    assert layer["status"] == "draft"
    assert layer["feature_count"] == 2
    assert layer["enabled"] is False


def test_import_bad_extension_http(client):
    r = client.post(
        "/api/v1/geo/import",
        headers={"X-Api-Key": EDITOR},
        files={"file": ("zone.shp", io.BytesIO(b".."), "application/octet-stream")},
        data={"name_fr": "Z"},
    )
    assert r.status_code == 400
    assert "Unsupported" in r.json()["detail"]


def test_import_oversized_http(client):
    big = b"x" * (MAX_BYTES + 1)
    r = client.post(
        "/api/v1/geo/import",
        headers={"X-Api-Key": EDITOR},
        files={"file": ("big.geojson", io.BytesIO(big), "application/geo+json")},
        data={"name_fr": "Big"},
    )
    assert r.status_code == 413


def test_import_invalid_geodata_http(client):
    r = client.post(
        "/api/v1/geo/import",
        headers={"X-Api-Key": EDITOR},
        files={"file": ("bad.geojson", io.BytesIO(b"not geojson"), "application/geo+json")},
        data={"name_fr": "Bad"},
    )
    assert r.status_code == 400


def test_import_path_traversal_filename(client):
    r = client.post(
        "/api/v1/geo/import",
        headers={"X-Api-Key": EDITOR},
        files={"file": ("../../etc/passwd.geojson", io.BytesIO(_GEOJSON_BYTES), "application/geo+json")},
        data={"name_fr": "Traversal"},
    )
    # Must either succeed safely (stem sanitised) or reject — never allow path traversal
    if r.status_code == 201:
        layer = r.json()["layer"]
        # Stored path must be inside project (no "..")
        assert ".." not in layer.get("file_path", "")
    else:
        assert r.status_code in (400, 422)


def test_import_json_extension_accepted(client):
    r = client.post(
        "/api/v1/geo/import",
        headers={"X-Api-Key": EDITOR},
        files={"file": ("zone.json", io.BytesIO(_GEOJSON_BYTES), "application/json")},
        data={"name_fr": "Zone JSON"},
    )
    assert r.status_code == 201

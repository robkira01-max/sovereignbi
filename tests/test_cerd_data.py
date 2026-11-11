"""Tests for P-041 — CERD Djibouti-ville SIG data integration."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("SOVEREIGN_EMBEDDER", "tfidf")

VIEWER = {"X-Api-Key": "test-viewer-key-s6"}

_REPO_ROOT = Path(__file__).parent.parent
CERD = _REPO_ROOT / "data" / "geo" / "cerd"
CATALOG = _REPO_ROOT / "data" / "geo" / "catalog.yaml"

CERD_LAYERS = [
    ("cerd_equipements_scolaires", "Polygon", (25, 40)),
    ("cerd_equipements_sociaux", "Polygon", (70, 95)),
    ("cerd_secteurs_adressage", "Polygon", (10, 20)),
    ("cerd_communes", "Polygon", (1, 5)),
    ("cerd_ilots", "Polygon", (3500, 4500)),
    ("cerd_lignes_bus", "LineString", (3, 8)),
    ("cerd_terminus_bus", "Point", (3, 10)),
    ("cerd_voirie", "LineString", (1200, 1600)),
    ("cerd_ouvrages", "Polygon", (15, 30)),
    ("cerd_typologies_urbaines", "Polygon", (20, 35)),
]

# Djibouti-ville bounding box (WGS84)
LON_MIN, LON_MAX = 43.05, 43.15
LAT_MIN, LAT_MAX = 11.53, 11.60


@pytest.mark.parametrize("layer_id,geom_type,count_range", CERD_LAYERS)
def test_cerd_geojson_exists(layer_id, geom_type, count_range):
    assert (CERD / f"{layer_id}.geojson").exists(), f"Missing: {layer_id}.geojson"


@pytest.mark.parametrize("layer_id,geom_type,count_range", CERD_LAYERS)
def test_cerd_geojson_feature_count(layer_id, geom_type, count_range):
    data = json.loads((CERD / f"{layer_id}.geojson").read_text())
    n = len(data["features"])
    lo, hi = count_range
    assert lo <= n <= hi, f"{layer_id}: expected {lo}–{hi} features, got {n}"


@pytest.mark.parametrize("layer_id,geom_type,count_range", CERD_LAYERS)
def test_cerd_geojson_geometry_type(layer_id, geom_type, count_range):
    data = json.loads((CERD / f"{layer_id}.geojson").read_text())
    assert data["type"] == "FeatureCollection"
    if data["features"]:
        actual = data["features"][0]["geometry"]["type"]
        assert actual == geom_type, f"{layer_id}: expected {geom_type}, got {actual}"


@pytest.mark.parametrize("layer_id,geom_type,count_range", CERD_LAYERS)
def test_cerd_geojson_coordinates_in_djibouti(layer_id, geom_type, count_range):
    data = json.loads((CERD / f"{layer_id}.geojson").read_text())
    for feat in data["features"]:
        geom = feat["geometry"]
        coords = _extract_first_coord(geom)
        if coords:
            lon, lat = coords
            assert LON_MIN <= lon <= LON_MAX, f"{layer_id}: lon {lon} outside Djibouti bbox"
            assert LAT_MIN <= lat <= LAT_MAX, f"{layer_id}: lat {lat} outside Djibouti bbox"


def _extract_first_coord(geom: dict) -> tuple[float, float] | None:
    """Return first (lon, lat) coordinate from any GeoJSON geometry."""
    gtype = geom["type"]
    coords = geom.get("coordinates")
    if not coords:
        return None
    if gtype == "Point":
        return (coords[0], coords[1])
    if gtype in ("LineString", "MultiPoint"):
        return (coords[0][0], coords[0][1])
    if gtype in ("Polygon", "MultiLineString"):
        return (coords[0][0][0], coords[0][0][1])
    if gtype == "MultiPolygon":
        return (coords[0][0][0][0], coords[0][0][0][1])
    return None


# ── schools specific checks ───────────────────────────────────────────────────

def test_schools_have_nom_field():
    data = json.loads((CERD / "cerd_equipements_scolaires.geojson").read_text())
    for f in data["features"]:
        assert "nom" in f["properties"], "schools missing nom field"


def test_schools_categorie_values():
    data = json.loads((CERD / "cerd_equipements_scolaires.geojson").read_text())
    cats = {f["properties"].get("categorie") for f in data["features"]}
    assert any("scolaire" in str(c).lower() for c in cats), f"Unexpected categories: {cats}"


# ── socioeconomic facilities checks ──────────────────────────────────────────

def test_socioeco_has_multiple_categories():
    data = json.loads((CERD / "cerd_equipements_sociaux.geojson").read_text())
    cats = {f["properties"].get("categorie") for f in data["features"]}
    assert len(cats) >= 4, f"Expected at least 4 categories, got {len(cats)}: {cats}"


# ── catalog registration ──────────────────────────────────────────────────────

def test_cerd_layers_in_catalog():
    import yaml
    catalog = yaml.safe_load(CATALOG.read_text())
    ids = {layer["id"] for layer in catalog["layers"]}
    for layer_id, _, _ in CERD_LAYERS:
        assert layer_id in ids, f"{layer_id} not registered in catalog.yaml"


def test_cerd_catalog_entries_have_required_fields():
    import yaml
    catalog = yaml.safe_load(CATALOG.read_text())
    cerd_entries = [l for l in catalog["layers"] if l["id"].startswith("cerd_")]
    assert len(cerd_entries) == 10, f"Expected 10 CERD layers, got {len(cerd_entries)}"
    for entry in cerd_entries:
        for field in ("id", "api_endpoint", "source", "status", "geometry_type"):
            assert field in entry, f"CERD layer {entry['id']} missing field: {field}"
        assert entry["status"] == "draft", f"{entry['id']} should be draft (license not public)"


# ── API routes ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


@pytest.mark.parametrize("layer_id,geom_type,count_range", CERD_LAYERS[:3])
def test_cerd_api_route(client, layer_id, geom_type, count_range):
    r = client.get(f"/api/v1/geo/dj/{layer_id}", headers=VIEWER)
    assert r.status_code == 200, f"{layer_id}: got {r.status_code}"
    data = r.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) >= count_range[0]


def test_cerd_api_404_for_unknown_level(client):
    r = client.get("/api/v1/geo/dj/cerd_nonexistent", headers=VIEWER)
    assert r.status_code == 404

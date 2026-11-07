"""Tests for GET /api/v1/geo/dj/{level} — Djibouti administrative GeoJSON."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("SOVEREIGN_EMBEDDER", "tfidf")

VIEWER = {"X-Api-Key": "test-viewer-key-s6"}

_REPO = Path(__file__).parent.parent
_GEO  = _REPO / "data" / "geo"
_ADM1 = _REPO / "frontend" / "src" / "data" / "dji_adm1.geojson"


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


# ── Route tests ───────────────────────────────────────────────────────────────

def test_geo_adm1_ok(client):
    r = client.get("/api/v1/geo/dj/adm1")
    assert r.status_code == 200
    fc = r.json()
    assert fc["type"] == "FeatureCollection"
    assert len(fc["features"]) == 6


def test_geo_adm2_ok(client):
    r = client.get("/api/v1/geo/dj/adm2")
    assert r.status_code == 200
    fc = r.json()
    assert fc["type"] == "FeatureCollection"
    assert len(fc["features"]) == 6


def test_geo_quartiers_ok(client):
    r = client.get("/api/v1/geo/dj/quartiers")
    assert r.status_code == 200
    fc = r.json()
    assert fc["type"] == "FeatureCollection"
    assert len(fc["features"]) >= 10


def test_geo_invalid_level(client):
    r = client.get("/api/v1/geo/dj/commune")
    assert r.status_code == 404


def test_geo_adm2_has_population(client):
    r = client.get("/api/v1/geo/dj/adm2")
    assert r.status_code == 200
    for feat in r.json()["features"]:
        p = feat["properties"]
        assert "population_est" in p
        assert p["population_est"] > 0


def test_geo_adm2_has_name(client):
    r = client.get("/api/v1/geo/dj/adm2")
    names = {f["properties"]["name"] for f in r.json()["features"]}
    assert "Djibouti" in names
    assert "Ali Sabieh" in names


def test_geo_quartiers_have_name(client):
    r = client.get("/api/v1/geo/dj/quartiers")
    names = {f["properties"]["name"] for f in r.json()["features"]}
    assert "Centre-ville" in names
    assert "Balbala Nord" in names


def test_geo_adm2_404_if_missing(client, tmp_path, monkeypatch):
    """When the file is missing, route returns 503 (not 500)."""
    import app.routers.geo as geo_mod
    fake_paths = dict(geo_mod._LEVEL_PATHS)
    fake_paths["adm2"] = tmp_path / "nonexistent.geojson"
    monkeypatch.setattr(geo_mod, "_LEVEL_PATHS", fake_paths)
    r = client.get("/api/v1/geo/dj/adm2")
    assert r.status_code == 503


# ── File validation tests (no HTTP) ──────────────────────────────────────────

def test_adm2_geojson_valid():
    path = _GEO / "dj_adm2.geojson"
    assert path.exists(), "data/geo/dj_adm2.geojson missing"
    fc = json.loads(path.read_text())
    assert fc["type"] == "FeatureCollection"
    assert all(f["geometry"]["type"] == "Polygon" for f in fc["features"])


def test_quartiers_geojson_valid():
    path = _GEO / "dj_quartiers.geojson"
    assert path.exists(), "data/geo/dj_quartiers.geojson missing"
    fc = json.loads(path.read_text())
    assert fc["type"] == "FeatureCollection"
    assert len(fc["features"]) >= 10


def test_quartiers_within_djibouti_bbox():
    """All quartier centroids should fall within the Djibouti bounding box."""
    fc = json.loads((_GEO / "dj_quartiers.geojson").read_text())
    # Rough DJ bbox: 41.7-43.6E, 10.9-12.8N
    for feat in fc["features"]:
        coords = feat["geometry"]["coordinates"][0]
        lons = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        assert min(lons) >= 41.5, f"{feat['properties']['name']}: lon {min(lons)} out of DJ bbox"
        assert max(lons) <= 44.0, f"{feat['properties']['name']}: lon {max(lons)} out of DJ bbox"
        assert min(lats) >= 10.5, f"{feat['properties']['name']}: lat {min(lats)} out of DJ bbox"
        assert max(lats) <= 12.9, f"{feat['properties']['name']}: lat {max(lats)} out of DJ bbox"


def test_adm2_total_population_plausible():
    fc = json.loads((_GEO / "dj_adm2.geojson").read_text())
    total = sum(f["properties"]["population_est"] for f in fc["features"])
    # Djibouti pop ~1M (±50%)
    assert 500_000 < total < 1_500_000, f"Total pop {total} implausible"


def test_adm2_licence_field():
    fc = json.loads((_GEO / "dj_adm2.geojson").read_text())
    for feat in fc["features"]:
        assert "source" in feat["properties"]
        assert "GADM" in feat["properties"]["source"]

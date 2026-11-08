"""Tests for P-023 — Moteur d'analyse spatiale DuckDB Spatial."""
from __future__ import annotations

import os
import pytest

os.environ.setdefault("SOVEREIGN_EMBEDDER", "tfidf")

VIEWER = {"X-Api-Key": "test-viewer-key-s6"}
EDITOR = {"X-Api-Key": "test-editor-key-s6"}


# ── SpatialEngine unit tests (no HTTP) ───────────────────────────────────────

def test_supported_analyses_non_empty():
    from app.geo_catalog.spatial_engine import SUPPORTED_ANALYSES
    assert len(SUPPORTED_ANALYSES) >= 5
    for key in ("area", "centroid", "bbox", "nearest", "summary"):
        assert key in SUPPORTED_ANALYSES


def test_engine_area_adm2():
    from app.geo_catalog.spatial_engine import SpatialEngine
    engine = SpatialEngine()
    results = engine.analyze("dj_adm2", "area", {})
    assert len(results) == 6
    for r in results:
        assert "name" in r
        assert "area_km2" in r
        assert r["area_km2"] > 0


def test_engine_area_largest_first():
    from app.geo_catalog.spatial_engine import SpatialEngine
    engine = SpatialEngine()
    results = engine.analyze("dj_adm2", "area", {})
    areas = [r["area_km2"] for r in results]
    assert areas == sorted(areas, reverse=True)


def test_engine_centroid_adm2():
    from app.geo_catalog.spatial_engine import SpatialEngine
    engine = SpatialEngine()
    results = engine.analyze("dj_adm2", "centroid", {})
    assert len(results) == 6
    for r in results:
        assert "name" in r
        # Djibouti bbox: lon ~41.7–43.5, lat ~10.9–12.7
        assert 41.0 < r["lon"] < 44.0
        assert 10.0 < r["lat"] < 13.0


def test_engine_centroid_adm1():
    from app.geo_catalog.spatial_engine import SpatialEngine
    engine = SpatialEngine()
    results = engine.analyze("dj_adm1", "centroid", {})
    assert len(results) == 6


def test_engine_bbox_adm2():
    from app.geo_catalog.spatial_engine import SpatialEngine
    engine = SpatialEngine()
    results = engine.analyze("dj_adm2", "bbox", {})
    assert len(results) == 6
    for r in results:
        assert r["min_lon"] < r["max_lon"]
        assert r["min_lat"] < r["max_lat"]


def test_engine_summary_adm2():
    from app.geo_catalog.spatial_engine import SpatialEngine
    engine = SpatialEngine()
    results = engine.analyze("dj_adm2", "summary", {})
    assert len(results) == 1
    s = results[0]
    assert s["feature_count"] == 6
    assert s["total_area_km2"] > 10_000   # Djibouti districts (approx geom) ~16k km²
    assert "extent" in s
    assert s["extent"]["min_lon"] < s["extent"]["max_lon"]


def test_engine_nearest_adm2():
    from app.geo_catalog.spatial_engine import SpatialEngine
    engine = SpatialEngine()
    # Query near Djibouti city (43.145, 11.589)
    results = engine.analyze("dj_adm2", "nearest", {"lon": 43.145, "lat": 11.589, "limit": 3})
    assert len(results) == 3
    # Djibouti region should be closest
    assert results[0]["name"] == "Djibouti"
    assert results[0]["dist_m"] < 50_000   # < 50 km


def test_engine_nearest_requires_params():
    from app.geo_catalog.spatial_engine import SpatialEngine
    engine = SpatialEngine()
    with pytest.raises(ValueError, match="nearest requires params"):
        engine.analyze("dj_adm2", "nearest", {})


def test_engine_unknown_layer_raises():
    from app.geo_catalog.spatial_engine import SpatialEngine
    engine = SpatialEngine()
    with pytest.raises(ValueError, match="Unknown layer"):
        engine.analyze("does_not_exist", "area", {})


def test_engine_unknown_analysis_raises():
    from app.geo_catalog.spatial_engine import SpatialEngine
    engine = SpatialEngine()
    with pytest.raises(ValueError, match="Unsupported analysis"):
        engine.analyze("dj_adm2", "unknown_analysis", {})


def test_engine_quartiers_area():
    from app.geo_catalog.spatial_engine import SpatialEngine
    engine = SpatialEngine()
    results = engine.analyze("dj_quartiers", "area", {})
    assert len(results) == 11
    assert all(r["area_km2"] > 0 for r in results)


# ── HTTP API tests ────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


def test_list_analysis_types(client):
    r = client.get("/api/v1/geo/analyze/types", headers=VIEWER)
    assert r.status_code == 200
    data = r.json()
    ids = {a["id"] for a in data["analyses"]}
    assert {"area", "centroid", "bbox", "nearest", "summary"}.issubset(ids)


def test_list_types_requires_auth(client):
    r = client.get("/api/v1/geo/analyze/types")
    assert r.status_code in (401, 403)


def test_run_area_adm2(client):
    r = client.post("/api/v1/geo/analyze", json={
        "layer_id": "dj_adm2", "analysis": "area", "params": {}
    }, headers=VIEWER)
    assert r.status_code == 200
    data = r.json()
    assert data["layer_id"] == "dj_adm2"
    assert data["analysis"] == "area"
    assert data["row_count"] == 6
    assert all("area_km2" in r for r in data["results"])


def test_run_centroid(client):
    r = client.post("/api/v1/geo/analyze", json={
        "layer_id": "dj_adm2", "analysis": "centroid", "params": {}
    }, headers=VIEWER)
    assert r.status_code == 200
    assert r.json()["row_count"] == 6


def test_run_summary(client):
    r = client.post("/api/v1/geo/analyze", json={
        "layer_id": "dj_adm2", "analysis": "summary", "params": {}
    }, headers=VIEWER)
    assert r.status_code == 200
    s = r.json()["results"][0]
    assert s["feature_count"] == 6
    assert s["total_area_km2"] > 10_000


def test_run_nearest(client):
    r = client.post("/api/v1/geo/analyze", json={
        "layer_id": "dj_adm2", "analysis": "nearest",
        "params": {"lon": 43.145, "lat": 11.589, "limit": 2}
    }, headers=VIEWER)
    assert r.status_code == 200
    data = r.json()
    assert data["row_count"] == 2
    assert data["results"][0]["name"] == "Djibouti"


def test_run_unknown_analysis_400(client):
    r = client.post("/api/v1/geo/analyze", json={
        "layer_id": "dj_adm2", "analysis": "fly_to_moon", "params": {}
    }, headers=VIEWER)
    assert r.status_code == 400


def test_run_unknown_layer_400(client):
    r = client.post("/api/v1/geo/analyze", json={
        "layer_id": "nonexistent", "analysis": "area", "params": {}
    }, headers=VIEWER)
    assert r.status_code == 400


def test_run_invalid_layer_id_400(client):
    r = client.post("/api/v1/geo/analyze", json={
        "layer_id": "../../etc/passwd", "analysis": "area", "params": {}
    }, headers=VIEWER)
    assert r.status_code == 400


def test_run_requires_auth(client):
    r = client.post("/api/v1/geo/analyze", json={
        "layer_id": "dj_adm2", "analysis": "area", "params": {}
    })
    assert r.status_code in (401, 403)


def test_run_quartiers_area(client):
    r = client.post("/api/v1/geo/analyze", json={
        "layer_id": "dj_quartiers", "analysis": "area", "params": {}
    }, headers=VIEWER)
    assert r.status_code == 200
    assert r.json()["row_count"] == 11

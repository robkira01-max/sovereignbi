"""Tests for the admin_pol layers (official Djibouti-ville quartiers and communes)."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("SOVEREIGN_EMBEDDER", "tfidf")

_GEO = Path(__file__).parent.parent / "data" / "geo"
_COMMUNES = {"Ras-Dika", "Boulaos", "Balbala"}


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


def _walk(c):
    if isinstance(c[0], (int, float)):
        yield c
    else:
        for i in c:
            yield from _walk(i)


def _load(name):
    return json.loads((_GEO / f"{name}.geojson").read_text())


def test_quartiers_count_and_properties():
    fc = _load("admin_quartiers")
    assert len(fc["features"]) == 91
    for f in fc["features"]:
        p = f["properties"]
        assert p["nom"].strip() and p["commune"] in _COMMUNES and p["superficie_ha"] > 0
        assert f["geometry"]["type"] in ("Polygon", "MultiPolygon")


def test_quartiers_per_commune():
    fc = _load("admin_quartiers")
    counts: dict[str, int] = {}
    for f in fc["features"]:
        counts[f["properties"]["commune"]] = counts.get(f["properties"]["commune"], 0) + 1
    assert counts == {"Boulaos": 46, "Balbala": 37, "Ras-Dika": 8}


def test_quartiers_reprojected_to_wgs84_over_djibouti_ville():
    for f in _load("admin_quartiers")["features"]:
        for lon, lat in _walk(f["geometry"]["coordinates"]):
            assert 43.0 < lon < 43.25 and 11.45 < lat < 11.7


def test_quartier_names_are_cleaned():
    noms = {f["properties"]["nom"] for f in _load("admin_quartiers")["features"]}
    assert "Centre Commercial et Administratif" in noms
    assert "Plateau du Serpent" in noms
    assert not any("' " in n or "Admnistratif" in n for n in noms)


def test_communes_cover_the_three_communes():
    fc = _load("admin_communes")
    assert {f["properties"]["nom"] for f in fc["features"]} == _COMMUNES
    assert sum(f["properties"]["nb_quartiers"] for f in fc["features"]) == 91


def test_catalog_registers_admin_layers():
    import yaml
    layers = {la["id"]: la for la in yaml.safe_load((_GEO / "catalog.yaml").read_text())["layers"]}
    assert layers["admin_quartiers"]["feature_count"] == 91
    assert layers["admin_communes"]["feature_count"] == 3
    for lid in ("admin_quartiers", "admin_communes"):
        assert (_GEO.parent.parent / layers[lid]["file_path"]).exists()


@pytest.mark.parametrize("level,n", [("admin_quartiers", 91), ("admin_communes", 3)])
def test_route_serves_admin_layers(client, level, n):
    r = client.get(f"/api/v1/geo/dj/{level}")
    assert r.status_code == 200
    assert len(r.json()["features"]) == n


import gzip

_TOPO = {"cerd_batiments": 86776, "cerd_routes": 1155, "cerd_hydro": 1554, "cerd_rail": 201, "cerd_sites": 1408}


@pytest.mark.parametrize("level,n", list(_TOPO.items()))
def test_cerd_topo_layers_served_gzipped(client, level, n):
    r = client.get(f"/api/v1/geo/dj/{level}")
    assert r.status_code == 200
    body = r.content
    fc = json.loads(gzip.decompress(body) if body[:2] == b"\x1f\x8b" else body)
    assert fc["type"] == "FeatureCollection"
    assert len(fc["features"]) == n


def test_cerd_buildings_are_typed_and_inside_the_city():
    fc = json.loads(gzip.decompress((_GEO / "cerd_batiments.geojson.gz").read_bytes()))
    cats = {f["properties"]["cat"] for f in fc["features"]}
    assert {"habitat", "education", "religion", "sante", "administration", "commerce"} <= cats
    assert all("type" in f["properties"] for f in fc["features"])
    for f in fc["features"][:2000]:
        for lon, lat in _walk(f["geometry"]["coordinates"]):
            assert 43.0 < lon < 43.25 and 11.45 < lat < 11.7
    types = {f["properties"]["type"] for f in fc["features"]}
    assert "Mosquée" in types and not any("?" in t or "ordinare" in t for t in types)


def test_osm_buildings_layer_was_replaced_by_the_official_survey():
    import yaml
    ids = {la["id"] for la in yaml.safe_load((_GEO / "catalog.yaml").read_text())["layers"]}
    assert "osm_batiments" not in ids
    assert set(_TOPO) <= ids
    assert not (_GEO / "osm_batiments.geojson.gz").exists()

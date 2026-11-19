"""Couches JICA : servies par l'API, catalogue cohérent (source JICA, licence non confirmée signalée)."""
from __future__ import annotations

import gzip
import json

import pytest
from fastapi.testclient import TestClient

from app.geo_catalog.registry import load_catalog
from app.main import app

IDS = ["jica_systemes_aquiferes", "jica_debit_aquiferes", "jica_pluie_moyenne", "jica_etp", "jica_etr",
       "jica_zones_climatiques", "jica_points_eau"]


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.mark.parametrize("lid", IDS)
def test_layer_is_served_as_gzip_geojson_within_djibouti(client, lid):
    r = client.get(f"/api/v1/geo/dj/{lid}")
    assert r.status_code == 200 and r.headers["content-encoding"] == "gzip"
    fc = r.json()
    assert fc["type"] == "FeatureCollection" and fc["features"]
    cat = next(l for l in load_catalog().layers if l.id == lid)
    assert len(fc["features"]) == cat.feature_count

    def pts(c):
        if isinstance(c[0], (int, float)):
            yield c
        else:
            for k in c:
                yield from pts(k)
    for f in fc["features"][:200]:
        for lon, lat, *_ in pts(f["geometry"]["coordinates"]):
            assert 41.5 < lon < 43.8 and 10.8 < lat < 13.1


def test_catalog_entries_name_jica_and_flag_unconfirmed_licence():
    layers = [l for l in load_catalog().layers if l.id.startswith("jica_")]
    assert sorted(l.id for l in layers) == sorted(IDS)
    for l in layers:
        assert "JICA" in l.source and "CERD" not in l.source
        assert "non confirmée" in l.license.lower() and l.status == "draft"
        assert l.warnings and "non confirmée" in l.warnings[0].fr.lower()


def test_unknown_jica_level_is_404(client):
    assert client.get("/api/v1/geo/dj/jica_inconnu").status_code == 404


def test_water_points_carry_only_name_and_region(client):
    fc = client.get("/api/v1/geo/dj/jica_points_eau").json()
    assert {tuple(sorted(f["properties"])) for f in fc["features"]} == {("nom", "region")}
    assert {f["properties"]["region"] for f in fc["features"]} == {"Ali-Sabieh", "Arta", "Obock", "Dikhil", "Tadjourah"}

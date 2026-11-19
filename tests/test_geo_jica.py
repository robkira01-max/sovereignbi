"""Couches JICA : servies par l'API, catalogue cohérent (source JICA, licence non confirmée signalée)."""
from __future__ import annotations

import gzip
import json

import pytest
from fastapi.testclient import TestClient

from app.geo_catalog.registry import load_catalog
from app.main import app

_BASE = ["jica_systemes_aquiferes", "jica_debit_aquiferes", "jica_pluie_moyenne", "jica_etp", "jica_etr",
       "jica_zones_climatiques", "jica_points_eau"]

IDS = sorted(l.id for l in load_catalog().layers if l.id.startswith("jica_"))


def test_expected_layer_families_are_present():
    assert set(_BASE) <= set(IDS) and len(IDS) >= 30
    for lid in ("jica_geologie_formations", "jica_hydrographie", "jica_vegetation_regions", "jica_sols_regions", "jica_sismicite"):
        assert lid in IDS


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
    for f in fc["features"][:300]:
        for lon, lat, *_ in pts(f["geometry"]["coordinates"]):
            assert 41.4 < lon < 44.1 and 10.4 < lat < 13.2     # la frontière dépasse légèrement le pays


def test_catalog_entries_name_jica_and_flag_unconfirmed_licence():
    layers = [l for l in load_catalog().layers if l.id.startswith("jica_")]
    assert sorted(l.id for l in layers) == IDS
    for l in layers:
        assert "JICA" in l.source and "CERD" not in l.source
        assert "non confirmée" in l.license.lower() and l.status == "draft"
        assert l.warnings and "non confirmée" in l.warnings[0].fr.lower()


def test_unknown_jica_level_is_404(client):
    assert client.get("/api/v1/geo/dj/jica_inconnu").status_code == 404


def test_water_points_carry_only_name_and_region(client):  # noqa: D103
    fc = client.get("/api/v1/geo/dj/jica_points_eau").json()
    assert {tuple(sorted(f["properties"])) for f in fc["features"]} == {("nom", "region")}
    assert {f["properties"]["region"] for f in fc["features"]} == {"Ali-Sabieh", "Arta", "Obock", "Dikhil", "Tadjourah"}


def test_every_catalogue_file_exists_and_json_is_strict():
    import pathlib
    for l in load_catalog().layers:
        if l.id.startswith("jica_"):
            raw = gzip.open(pathlib.Path(l.file_path), "rt", encoding="utf-8").read()
            assert "Infinity" not in raw and "NaN" not in raw
            json.loads(raw)


def test_assumed_projection_is_flagged_in_catalogue():
    for lid in ("jica_vegetation_regions", "jica_sismicite", "jica_sols_regions"):
        l = next(x for x in load_catalog().layers if x.id == lid)
        assert any("supposée" in w.fr for w in l.warnings)

"""Tests for P-042 — Djibouti health data (structures, indicators, PCIME, GeoJSON route)."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import pytest

os.environ.setdefault("SOVEREIGN_EMBEDDER", "tfidf")

VIEWER = {"X-Api-Key": "test-viewer-key-s6"}

DATA_ROOT = Path(__file__).parent.parent / "data"
INSTAD = DATA_ROOT / "instad"
GEO = DATA_ROOT / "geo"


# ── CSV data quality ──────────────────────────────────────────────────────────

def test_structures_csv_no_subtotals():
    df = pd.read_csv(INSTAD / "structures_sante.csv")
    assert not df["structure"].str.contains("Région|Ensemble du pays", na=False).any(), \
        "CSV should not contain region subtotals"


def test_structures_csv_row_count():
    df = pd.read_csv(INSTAD / "structures_sante.csv")
    assert 60 <= len(df) <= 85, f"Expected ~73 structures, got {len(df)}"


def test_structures_csv_required_columns():
    df = pd.read_csv(INSTAD / "structures_sante.csv")
    for col in ["region", "structure", "total_personnel", "medecin_gen", "infirmier_de", "lat", "lon"]:
        assert col in df.columns, f"Missing column: {col}"


def test_structures_csv_regions():
    df = pd.read_csv(INSTAD / "structures_sante.csv")
    regions = set(df["region"].dropna().str.strip())
    for expected in ["Ali-Sabieh", "Arta", "Dikhil", "djibouti_ville", "Obock", "Tadjourah"]:
        assert expected in regions, f"Missing region: {expected}"


def test_indicateurs_csv_row_count():
    df = pd.read_csv(INSTAD / "indicateurs_sante.csv")
    assert 30 <= len(df) <= 45, f"Expected ~39 indicators, got {len(df)}"


def test_indicateurs_csv_has_national_columns():
    df = pd.read_csv(INSTAD / "indicateurs_sante.csv")
    for col in ["national_2019", "national_2020", "national_evol"]:
        assert col in df.columns, f"Missing column: {col}"


def test_indicateurs_vaccination_penta3():
    df = pd.read_csv(INSTAD / "indicateurs_sante.csv")
    row = df[df["indicateur"].str.contains("Pentavalent 3", na=False)]
    assert len(row) == 1
    assert 60 <= float(row["national_2020"].iloc[0]) <= 90, "Penta3 coverage out of range"


def test_pcime_csv_no_subtotals():
    df = pd.read_csv(INSTAD / "pcime_enfants.csv")
    assert not df["structure"].str.contains("Région|Ensemble", na=False).any(), \
        "PCIME CSV should not contain region subtotals"


def test_pcime_csv_required_columns():
    df = pd.read_csv(INSTAD / "pcime_enfants.csv")
    for col in ["region", "structure", "enfants_examines", "pneumonie", "diarrhees", "anemies"]:
        assert col in df.columns, f"Missing column: {col}"


def test_pcime_national_total_enfants():
    df = pd.read_csv(INSTAD / "pcime_enfants.csv")
    total = df["enfants_examines"].sum()
    assert 50_000 <= total <= 70_000, f"National PCIME total out of range: {total}"


# ── GeoJSON structure ─────────────────────────────────────────────────────────

def test_sante_geojson_exists():
    assert (GEO / "dj_structures_sante.geojson").exists()


def test_sante_geojson_valid():
    content = json.loads((GEO / "dj_structures_sante.geojson").read_text())
    assert content["type"] == "FeatureCollection"
    assert 60 <= len(content["features"]) <= 75, \
        f"Expected ~65 features, got {len(content['features'])}"


def test_sante_geojson_coordinates_in_djibouti():
    content = json.loads((GEO / "dj_structures_sante.geojson").read_text())
    for f in content["features"]:
        lon, lat = f["geometry"]["coordinates"]
        # Djibouti bounding box: lon 41.7-43.5, lat 10.9-12.7
        assert 41.0 <= lon <= 44.0, f"Unexpected longitude {lon} for {f['properties']['structure']}"
        assert 10.5 <= lat <= 13.0, f"Unexpected latitude {lat} for {f['properties']['structure']}"


def test_sante_geojson_properties():
    content = json.loads((GEO / "dj_structures_sante.geojson").read_text())
    for f in content["features"]:
        props = f["properties"]
        assert "region" in props
        assert "structure" in props
        assert "type" in props
        assert "total_personnel" in props
        assert isinstance(props["total_personnel"], int)


def test_sante_geojson_structure_types():
    content = json.loads((GEO / "dj_structures_sante.geojson").read_text())
    types = {f["properties"]["type"] for f in content["features"]}
    assert "centre_sante" in types or "poste_sante" in types
    assert "hôpital" in types


# ── API route ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


def test_geo_structures_sante_route(client):
    r = client.get("/api/v1/geo/dj/structures_sante", headers=VIEWER)
    assert r.status_code == 200
    data = r.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) >= 60


def test_geo_invalid_level_still_404(client):
    r = client.get("/api/v1/geo/dj/unknown_level", headers=VIEWER)
    assert r.status_code == 404


# ── Dashboard YAML ────────────────────────────────────────────────────────────

def test_sante_dashboard_yaml_exists():
    assert (DATA_ROOT / "dashboards" / "sante-djibouti-2020.yaml").exists()


def test_sante_dashboard_yaml_loads():
    import yaml
    path = DATA_ROOT / "dashboards" / "sante-djibouti-2020.yaml"
    d = yaml.safe_load(path.read_text())
    assert d["id"] == "sante-djibouti-2020"
    assert len(d["tiles"]) >= 6
    # Every tile must have a source attribution
    for tile in d["tiles"]:
        assert tile.get("source"), f"Tile {tile['id']} missing source"


def test_sante_dashboard_sql_queries():
    import yaml, duckdb, pandas as pd
    path = DATA_ROOT / "dashboards" / "sante-djibouti-2020.yaml"
    d = yaml.safe_load(path.read_text())

    con = duckdb.connect(":memory:")
    for name in ["structures_sante", "indicateurs_sante", "pcime_enfants"]:
        df = pd.read_csv(INSTAD / f"{name}.csv")
        con.register("_tmp", df)
        con.execute(f'CREATE TABLE "{name}" AS SELECT * FROM _tmp')
        con.unregister("_tmp")

    for tile in d["tiles"]:
        sql = tile.get("sql_pinned", "").strip()
        if not sql:
            continue
        try:
            cols, rows = con.execute(sql).description, con.execute(sql).fetchall()
            assert rows is not None
        except Exception as e:
            pytest.fail(f"Tile '{tile['id']}' SQL error: {e}\nSQL: {sql[:200]}")

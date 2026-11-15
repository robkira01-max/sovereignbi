"""P-066 : routes SDMX — export de tuile, import, catalogue d'indicateurs."""
from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

os.environ.setdefault("SOVEREIGN_EMBEDDER", "tfidf")

VIEWER = {"X-Api-Key": "test-viewer-key-s6"}
EDITOR = {"X-Api-Key": "test-editor-key-s6"}

SQL = ("SELECT 'Obock' AS region, 2023 AS annee, 29.1 AS taux "
       "UNION ALL SELECT 'Tadjourah', 2023, 27.4 UNION ALL SELECT 'Obock', 2024, 28.0")

FILE = (b"STRUCTURE,STRUCTURE_ID,ACTION,REF_AREA,TIME_PERIOD,OBS_VALUE\n"
        b"dataflow,INSTAD:CHOMAGE(1.0),I,DJ,2023,28.4\n"
        b"dataflow,INSTAD:CHOMAGE(1.0),I,DJ,2024,27.9\n")


@pytest.fixture()
def client(monkeypatch):
    from app.data.duckdb_store import DataStore
    from app.main import app

    monkeypatch.delenv("SOVEREIGN_DB_PATH", raising=False)
    # Jamais d'affectation directe de app.state.store : elle fuirait vers les tests suivants.
    monkeypatch.setattr(app.state, "store", DataStore(), raising=False)
    with TestClient(app) as c:
        yield c
    app.state.active_sector_id = None
    app.state.active_semantic_text = None


def _dash(tmp_path: Path, monkeypatch, sql: str = SQL, dash_id: str = "d-sdmx") -> str:
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    tile = {"id": "t1", "type": "table", "title": "Chômage", "sql_pinned": sql}
    data = {"id": dash_id, "title": "T", "scope": "personal", "tiles": [tile],
            "theme": {"primary_color": "#1a4a8c", "font": "sans-serif", "logo_url": ""},
            "created_at": "", "updated_at": ""}
    (tmp_path / f"{dash_id}.yaml").write_text(yaml.safe_dump(data))
    return dash_id


def export(client, dash, **params):
    return client.get(f"/dashboards/{dash}/tiles/t1/export/sdmx-csv", params=params, headers=VIEWER)


# ── export ────────────────────────────────────────────────────────────────────

def test_export_infers_time_and_value_columns(client, tmp_path, monkeypatch):
    r = export(client, _dash(tmp_path, monkeypatch))
    assert r.status_code == 200, r.text
    assert "sdmx" in r.headers["content-type"] and ".sdmx.csv" in r.headers["content-disposition"]
    lines = r.text.splitlines()
    assert lines[0] == "STRUCTURE,STRUCTURE_ID,ACTION,REGION,TIME_PERIOD,OBS_VALUE"
    assert lines[1].startswith("dataflow,MIZANBI:D_SDMX_T1(1.0),I,Obock,2023,29.1")
    assert len(lines) == 4


def test_export_options_unit_structure_and_columns(client, tmp_path, monkeypatch):
    r = export(client, _dash(tmp_path, monkeypatch), structure_id="INSTAD:CHOMAGE(2.1)", unit="PCT",
               time_col="annee", value_col="taux")
    lines = r.text.splitlines()
    assert lines[0].endswith("OBS_VALUE,UNIT_MEASURE")
    assert lines[1].startswith("dataflow,INSTAD:CHOMAGE(2.1),I,") and lines[1].endswith(",PCT")


def test_export_errors_are_422_with_a_message(client, tmp_path, monkeypatch):
    d = _dash(tmp_path, monkeypatch)
    assert export(client, d, structure_id="pas valide").status_code == 422
    assert export(client, d, value_col="inconnue").status_code == 422
    d2 = _dash(tmp_path, monkeypatch, sql="SELECT 'a' AS x, 'b' AS y", dash_id="d-sdmx-2")
    r = export(client, d2)
    assert r.status_code == 422 and "OBS_VALUE" in r.json()["detail"]
    assert client.get("/dashboards/absent/tiles/t1/export/sdmx-csv", headers=VIEWER).status_code == 404


def test_export_requires_authentication_and_validates_freq(client, tmp_path, monkeypatch):
    d = _dash(tmp_path, monkeypatch)
    assert client.get(f"/dashboards/{d}/tiles/t1/export/sdmx-csv").status_code == 401
    assert export(client, d, freq="Z").status_code == 422


# ── import ────────────────────────────────────────────────────────────────────

def imp(client, content=FILE, headers=EDITOR, **params):
    return client.post("/sdmx/import", params=params, files={"file": ("f.csv", content, "text/csv")}, headers=headers)


def test_import_requires_editor(client):
    assert client.post("/sdmx/import", files={"file": ("f.csv", FILE)}).status_code == 401
    assert imp(client, headers=VIEWER).status_code == 403


def test_import_loads_a_prefixed_table_and_it_is_queryable(client):
    r = imp(client)
    assert r.status_code == 200
    body = r.json()
    assert body["loaded"] is True and body["table"] == "sdmx_chomage" and body["rows"] == 2
    assert body["columns"] == ["REF_AREA", "TIME_PERIOD", "OBS_VALUE"]
    from app.main import app
    cols, rows = app.state.store.execute('SELECT ref_area, time_period, obs_value FROM "sdmx_chomage" ORDER BY 2')
    assert rows == [("DJ", "2023", 28.4), ("DJ", "2024", 27.9)]


def test_import_dry_run_validates_without_loading(client):
    r = imp(client, dry_run="true")
    assert r.status_code == 200 and r.json()["loaded"] is False
    from app.main import app
    assert "sdmx_chomage" not in app.state.store.tables


def test_import_refuses_overwrite_unless_replace(client):
    assert imp(client).status_code == 200
    assert imp(client).status_code == 409
    assert imp(client, replace="true").status_code == 200


def test_import_cannot_overwrite_a_non_sdmx_table(client):
    from app.main import app
    import pandas as pd
    app.state.store.load_dataframe("ventes", pd.DataFrame({"a": [1]}))
    r = imp(client, table="ventes", replace="true")
    assert r.json()["table"] == "sdmx_ventes"           # préfixe forcé
    assert app.state.store.execute("SELECT a FROM ventes")[1] == [(1,)]


@pytest.mark.parametrize("name", ["1abc", "a b", "a;DROP", "x" * 70, "é"])
def test_import_rejects_unsafe_table_names(client, name):
    assert imp(client, table=name).status_code in (422,)


def test_import_rejects_bad_content(client):
    assert imp(client, content=b"<?xml version='1.0'?><Structure/>").status_code == 400      # SDMX-ML non pris en charge
    assert imp(client, content=b"\xff\xfe\x00bad").status_code == 400                        # pas UTF-8
    r = imp(client, content=b"STRUCTURE,STRUCTURE_ID,ACTION,OBS_VALUE\ndataflow,X:Y(1.0),I,abc\n")
    assert r.status_code == 422 and "Ligne 2" in r.json()["detail"]
    r = imp(client, content=b"STRUCTURE,STRUCTURE_ID,ACTION,OBS_VALUE\ndataflow,X:Y(1.0),D,1\n")
    assert r.status_code == 422 and "suppression" in r.json()["detail"]


def test_import_enforces_the_size_limit(client, monkeypatch):
    monkeypatch.setattr("app.routers.sdmx._MAX_BYTES", 100)
    assert imp(client, content=FILE + b"x" * 200).status_code == 413


# ── catalogue d'indicateurs ───────────────────────────────────────────────────

def test_indicator_catalogue_follows_the_active_sector(client):
    assert client.get("/semantic/indicators").status_code == 401
    assert client.get("/semantic/indicators", headers=VIEWER).json()["count"] == 0     # modèle par défaut : aucun code
    assert client.post("/semantic/sectors/instad_statistics/activate", headers=EDITOR).status_code == 200
    body = client.get("/semantic/indicators", headers=VIEWER).json()
    codes = {i["code"] for i in body["indicators"]}
    assert {"PIB_TOTAL", "INFLATION"} <= codes
    pib = client.get("/semantic/indicators/PIB_TOTAL", headers=VIEWER).json()
    assert pib["frequency"] == "A" and pib["frequency_label"] == "annuelle" and "fictives" in pib["source"]
    assert pib["complete"] is False and "unit" in pib["missing"]      # ce qui manque est dit
    assert client.get("/semantic/indicators", params={"topic": "economie"}, headers=VIEWER).json()["count"] >= 4
    assert client.get("/semantic/indicators", params={"topic": "autre"}, headers=VIEWER).json()["count"] == 0
    assert client.get("/semantic/indicators/INCONNU", headers=VIEWER).status_code == 404

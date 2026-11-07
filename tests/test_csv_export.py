"""Tests for GET /dashboards/{id}/tiles/{id}/export/csv."""
from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

os.environ.setdefault("SOVEREIGN_EMBEDDER", "tfidf")

VIEWER = {"X-Api-Key": "test-viewer-key-s6"}


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


def _write_yaml(tmp_path: Path, dash_id: str, sql: str = "SELECT 25.0 AS taux") -> None:
    tile = {"id": "kpi1", "type": "kpi", "title": "Chômage", "sql_pinned": sql}
    data = {
        "id": dash_id, "title": "T", "scope": "personal",
        "tiles": [tile],
        "theme": {"primary_color": "#1a4a8c", "font": "sans-serif", "logo_url": ""},
        "created_at": "", "updated_at": "",
    }
    (tmp_path / f"{dash_id}.yaml").write_text(yaml.safe_dump(data))


def test_csv_200_and_mime(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    _write_yaml(tmp_path, "d-csv-1")
    r = client.get("/dashboards/d-csv-1/tiles/kpi1/export/csv", headers=VIEWER)
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]


def test_csv_has_bom_and_header(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    _write_yaml(tmp_path, "d-csv-2")
    r = client.get("/dashboards/d-csv-2/tiles/kpi1/export/csv", headers=VIEWER)
    raw = r.content
    # UTF-8 BOM
    assert raw[:3] == b"\xef\xbb\xbf"
    text = raw.decode("utf-8-sig")
    lines = [l for l in text.splitlines() if l.strip()]
    # First line is column header
    assert lines[0] == "taux"
    # Second line is data
    assert "25.0" in lines[1]


def test_csv_content_disposition(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    _write_yaml(tmp_path, "d-csv-3")
    r = client.get("/dashboards/d-csv-3/tiles/kpi1/export/csv", headers=VIEWER)
    cd = r.headers.get("content-disposition", "")
    assert "attachment" in cd
    assert "d-csv-3-kpi1.csv" in cd


def test_csv_multiple_columns(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    _write_yaml(tmp_path, "d-csv-4", sql="SELECT 2024 AS annee, 15.3 AS taux, 'DJ' AS pays")
    r = client.get("/dashboards/d-csv-4/tiles/kpi1/export/csv", headers=VIEWER)
    text = r.content.decode("utf-8-sig")
    lines = [l for l in text.splitlines() if l.strip()]
    assert "annee" in lines[0]
    assert "taux" in lines[0]
    assert "pays" in lines[0]
    assert "2024" in lines[1]


def test_csv_missing_dashboard(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    r = client.get("/dashboards/ghost-csv/tiles/kpi1/export/csv", headers=VIEWER)
    assert r.status_code == 404


def test_csv_requires_auth(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    _write_yaml(tmp_path, "d-csv-auth")
    r = client.get("/dashboards/d-csv-auth/tiles/kpi1/export/csv")
    assert r.status_code == 401

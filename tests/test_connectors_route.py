"""Tests des routes /connectors (MySQL et MSSQL mockés)."""
from __future__ import annotations

import os
from unittest.mock import patch, MagicMock

import pandas as pd
import pytest
from fastapi.testclient import TestClient

_EDITOR_KEY = os.environ.get("SOVEREIGN_EDITOR_KEY", "test-editor-key-s6")
_VIEWER_KEY = os.environ.get("SOVEREIGN_VIEWER_KEY", "test-viewer-key-s6")
_E = {"X-Api-Key": _EDITOR_KEY}
_V = {"X-Api-Key": _VIEWER_KEY}


@pytest.fixture
def client():
    import app.main as m
    from app.data.duckdb_store import DataStore

    fresh_store = DataStore()
    original_store = m.store
    original_state_store = m.app.state.store
    m.store = fresh_store
    m.app.state.store = fresh_store
    yield TestClient(m.app)
    m.store = original_store
    m.app.state.store = original_state_store


def test_mysql_route_requires_editor_role(client):
    r = client.post("/connectors/mysql", json={"table": "t", "database": "db"}, headers=_V)
    assert r.status_code == 403


def test_mysql_route_loads_table_in_store(client):
    df = pd.DataFrame({"id": [1, 2], "val": ["a", "b"]})
    with patch("app.routers.connectors.load_mysql_table", return_value=df):
        r = client.post(
            "/connectors/mysql",
            json={"table": "commandes", "database": "sales"},
            headers=_E,
        )
    assert r.status_code == 200
    data = r.json()
    assert data["rows"] == 2
    assert "commandes" in data["table"]


def test_mysql_route_returns_503_on_connection_error(client):
    with patch("app.routers.connectors.load_mysql_table", side_effect=Exception("refused")):
        r = client.post(
            "/connectors/mysql",
            json={"table": "t", "database": "db"},
            headers=_E,
        )
    assert r.status_code == 503


def test_mssql_route_requires_editor_role(client):
    r = client.post("/connectors/mssql", json={"table": "t", "database": "db"}, headers=_V)
    assert r.status_code == 403


def test_mssql_route_loads_table_in_store(client):
    df = pd.DataFrame({"id": [1], "val": ["x"]})
    with patch("app.routers.connectors.load_mssql_table", return_value=df):
        r = client.post(
            "/connectors/mssql",
            json={"table": "ventes", "database": "erp"},
            headers=_E,
        )
    assert r.status_code == 200
    assert r.json()["rows"] == 1


def test_mssql_route_returns_503_on_error(client):
    with patch("app.routers.connectors.load_mssql_table", side_effect=Exception("timeout")):
        r = client.post(
            "/connectors/mssql",
            json={"table": "t", "database": "db"},
            headers=_E,
        )
    assert r.status_code == 503


def test_list_connectors_requires_viewer_role(client):
    r = client.get("/connectors")
    assert r.status_code == 401


def test_list_connectors_with_viewer_key(client):
    r = client.get("/connectors", headers=_V)
    assert r.status_code == 200
    assert "connectors" in r.json()

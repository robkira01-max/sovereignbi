"""Tests connecteurs Sprint 14 : Snowflake, BigQuery, MongoDB."""
import pandas as pd
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app, store
from app.data.snowflake_store import _quote_sf_ident, load_snowflake_table
from app.data.bigquery_store import _quote_bq_ident, load_bigquery_table
from app.data.mongodb_store import load_mongodb_collection

EDITOR = {"X-Api-Key": "test-editor-key-s6"}
VIEWER = {"X-Api-Key": "test-viewer-key-s6"}


@pytest.fixture
def client():
    return TestClient(app)


# --- Snowflake unit ---

def test_quote_sf_ident_valid():
    assert _quote_sf_ident("my_table") == '"my_table"'


def test_quote_sf_ident_invalid():
    with pytest.raises(ValueError):
        _quote_sf_ident("bad-name")


def test_load_snowflake_missing_driver():
    with patch.dict("sys.modules", {"snowflake": None, "snowflake.connector": None}):
        with pytest.raises((ImportError, TypeError)):
            load_snowflake_table("t", "db", account="acct", user="u", password="p")


def test_load_snowflake_mock():
    df_expected = pd.DataFrame({"id": [1, 2], "name": ["Alice", "Bob"]})
    with patch("app.data.snowflake_store.load_snowflake_table", return_value=df_expected) as mock_fn:
        result = mock_fn("users", "mydb", account="acc", user="u", password="p")
    assert list(result.columns) == ["id", "name"]
    assert len(result) == 2


# --- BigQuery unit ---

def test_quote_bq_ident_valid():
    assert _quote_bq_ident("my_table") == "`my_table`"


def test_quote_bq_ident_invalid():
    with pytest.raises(ValueError):
        _quote_bq_ident("bad name!")


def test_load_bigquery_missing_driver():
    with patch.dict("sys.modules", {"google": None, "google.cloud": None, "google.cloud.bigquery": None, "google.oauth2": None, "google.oauth2.service_account": None}):
        with pytest.raises((ImportError, TypeError)):
            load_bigquery_table("t", "ds", "proj")


def test_load_bigquery_mock():
    df_expected = pd.DataFrame({"id": [1, 2], "val": ["a", "b"]})
    with patch("app.data.bigquery_store.load_bigquery_table", return_value=df_expected) as mock_fn:
        df = mock_fn("t", "ds", "proj")
    assert list(df.columns) == ["id", "val"]


# --- MongoDB unit ---

def test_load_mongodb_missing_driver():
    with patch.dict("sys.modules", {"pymongo": None}):
        with pytest.raises((ImportError, TypeError)):
            load_mongodb_collection("col", "db")


def test_load_mongodb_mock():
    mock_client = MagicMock()
    mock_col = MagicMock()
    mock_col.find.return_value = [{"_id": "abc", "x": 1}, {"_id": "def", "x": 2}]
    mock_client.__getitem__.return_value.__getitem__.return_value = mock_col
    mock_pymongo = MagicMock()
    mock_pymongo.MongoClient.return_value = mock_client
    with patch.dict("sys.modules", {"pymongo": mock_pymongo}):
        df = load_mongodb_collection("col", "db")
    assert "_id" in df.columns
    assert len(df) == 2
    assert df["_id"].astype(str).tolist() == ["abc", "def"]


def test_load_mongodb_empty():
    mock_client = MagicMock()
    mock_col = MagicMock()
    mock_col.find.return_value = []
    mock_client.__getitem__.return_value.__getitem__.return_value = mock_col
    mock_pymongo = MagicMock()
    mock_pymongo.MongoClient.return_value = mock_client
    with patch.dict("sys.modules", {"pymongo": mock_pymongo}):
        df = load_mongodb_collection("col", "db")
    assert df.empty


# --- Route tests ---

def test_connector_snowflake_501_no_driver(client):
    with patch("app.routers.connectors.load_snowflake_table", side_effect=ImportError("no driver")):
        r = client.post("/connectors/snowflake", json={
            "table": "t", "database": "db", "account": "acc",
        }, headers=EDITOR)
    assert r.status_code == 501


def test_connector_snowflake_503_connection_error(client):
    with patch("app.routers.connectors.load_snowflake_table", side_effect=Exception("timeout")):
        r = client.post("/connectors/snowflake", json={
            "table": "t", "database": "db",
        }, headers=EDITOR)
    assert r.status_code == 503


def test_connector_bigquery_501_no_driver(client):
    with patch("app.routers.connectors.load_bigquery_table", side_effect=ImportError("no driver")):
        r = client.post("/connectors/bigquery", json={
            "table": "t", "dataset": "ds", "project": "proj",
        }, headers=EDITOR)
    assert r.status_code == 501


def test_connector_mongodb_501_no_driver(client):
    with patch("app.routers.connectors.load_mongodb_collection", side_effect=ImportError("no driver")):
        r = client.post("/connectors/mongodb", json={
            "collection": "c", "database": "db",
        }, headers=EDITOR)
    assert r.status_code == 501


def test_connector_snowflake_loads_dataframe(client):
    df = pd.DataFrame({"id": [1, 2], "val": ["a", "b"]})
    with patch("app.routers.connectors.load_snowflake_table", return_value=df):
        r = client.post("/connectors/snowflake", json={
            "table": "t", "database": "db",
        }, headers=EDITOR)
    assert r.status_code == 200
    assert r.json()["rows"] == 2


def test_connector_bigquery_loads_dataframe(client):
    df = pd.DataFrame({"id": [1], "val": ["x"]})
    with patch("app.routers.connectors.load_bigquery_table", return_value=df):
        r = client.post("/connectors/bigquery", json={
            "table": "t", "dataset": "ds", "project": "proj",
        }, headers=EDITOR)
    assert r.status_code == 200
    assert r.json()["rows"] == 1


def test_connector_mongodb_loads_dataframe(client):
    df = pd.DataFrame({"_id": ["abc"], "name": ["test"]})
    with patch("app.routers.connectors.load_mongodb_collection", return_value=df):
        r = client.post("/connectors/mongodb", json={
            "collection": "c", "database": "db",
        }, headers=EDITOR)
    assert r.status_code == 200
    assert r.json()["rows"] == 1


def test_list_connectors_includes_new_types(client):
    df = pd.DataFrame({"x": [1]})
    with patch("app.routers.connectors.load_mongodb_collection", return_value=df):
        client.post("/connectors/mongodb", json={
            "collection": "items", "database": "mydb",
        }, headers=EDITOR)
    r = client.get("/connectors", headers=VIEWER)
    assert r.status_code == 200
    types = [c["type"] for c in r.json()["connectors"]]
    assert "mongodb" in types

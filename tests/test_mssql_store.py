"""Tests du connecteur SQL Server (sans vraie DB — pymssql.connect mocké)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

pymssql = pytest.importorskip("pymssql")

from app.data.mssql_store import _parse_mssql_dsn, _quote_mssql_ident, load_mssql_table


def test_quote_mssql_ident_valid():
    assert _quote_mssql_ident("ma_table") == "[ma_table]"


def test_quote_mssql_ident_uppercase():
    assert _quote_mssql_ident("MyDB") == "[MyDB]"


def test_quote_mssql_ident_rejects_dash():
    with pytest.raises(ValueError):
        _quote_mssql_ident("my-table")


def test_quote_mssql_ident_rejects_space():
    with pytest.raises(ValueError):
        _quote_mssql_ident("my table")


def test_quote_mssql_ident_rejects_injection():
    with pytest.raises(ValueError):
        _quote_mssql_ident("[evil]")


def test_quote_mssql_ident_rejects_empty():
    with pytest.raises(ValueError):
        _quote_mssql_ident("")


def test_parse_mssql_dsn_full():
    p = _parse_mssql_dsn("mssql://user:pass@myserver:1434/mydb")
    assert p["server"] == "myserver"
    assert p["port"] == 1434
    assert p["user"] == "user"
    assert p["password"] == "pass"
    assert p["database"] == "mydb"


def test_parse_mssql_dsn_defaults():
    p = _parse_mssql_dsn("mssql://localhost/testdb")
    assert p["server"] == "localhost"
    assert p["port"] == 1433
    assert p["database"] == "testdb"


@patch("pymssql.connect")
def test_load_mssql_table_calls_correct_query(mock_connect):
    df_expected = pd.DataFrame({"id": [1], "val": ["x"]})
    with patch("pandas.read_sql", return_value=df_expected) as mock_sql:
        mock_connect.return_value = MagicMock()
        mock_connect.return_value.close = MagicMock()
        result = load_mssql_table(table="orders", database="sales")
        call_args = mock_sql.call_args[0][0]
        assert "[orders]" in call_args
        assert "[sales]" in call_args


@patch("pymssql.connect")
def test_load_mssql_table_uses_env_dsn(mock_connect, monkeypatch):
    monkeypatch.setenv("MSSQL_DSN", "mssql://envuser:envpass@envserver:1433/envdb")
    df_expected = pd.DataFrame({"col": [1]})
    with patch("pandas.read_sql", return_value=df_expected):
        mock_connect.return_value = MagicMock()
        mock_connect.return_value.close = MagicMock()
        load_mssql_table(table="t", database="d")
    call_kwargs = mock_connect.call_args[1]
    assert call_kwargs.get("server") == "envserver"

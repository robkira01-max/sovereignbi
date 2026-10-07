"""Tests du connecteur MySQL (sans vraie DB — pymysql.connect mocké)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from app.data.mysql_store import _parse_mysql_dsn, _quote_mysql_ident, load_mysql_table


def test_quote_mysql_ident_valid():
    assert _quote_mysql_ident("ma_table") == "`ma_table`"


def test_quote_mysql_ident_uppercase():
    assert _quote_mysql_ident("MyDB") == "`MyDB`"


def test_quote_mysql_ident_rejects_dash():
    with pytest.raises(ValueError):
        _quote_mysql_ident("my-table")


def test_quote_mysql_ident_rejects_space():
    with pytest.raises(ValueError):
        _quote_mysql_ident("my table")


def test_quote_mysql_ident_rejects_injection():
    with pytest.raises(ValueError):
        _quote_mysql_ident("`evil`")


def test_quote_mysql_ident_rejects_empty():
    with pytest.raises(ValueError):
        _quote_mysql_ident("")


def test_parse_mysql_dsn_full():
    p = _parse_mysql_dsn("mysql://user:pass@myhost:3307/mydb")
    assert p["host"] == "myhost"
    assert p["port"] == 3307
    assert p["user"] == "user"
    assert p["password"] == "pass"
    assert p["database"] == "mydb"


def test_parse_mysql_dsn_defaults():
    p = _parse_mysql_dsn("mysql://localhost/testdb")
    assert p["host"] == "localhost"
    assert p["port"] == 3306
    assert p["database"] == "testdb"


def _make_mock_conn(data: list[tuple], cols: list[str]):
    mock_cur = MagicMock()
    mock_cur.description = [(c, None, None, None, None, None, None) for c in cols]
    mock_cur.fetchall.return_value = data
    mock_conn = MagicMock()
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return mock_conn


@patch("pymysql.connect")
def test_load_mysql_table_calls_correct_query(mock_connect):
    df_expected = pd.DataFrame({"id": [1, 2], "name": ["a", "b"]})
    with patch("pandas.read_sql", return_value=df_expected) as mock_sql:
        mock_connect.return_value = MagicMock()
        mock_connect.return_value.close = MagicMock()
        result = load_mysql_table(table="orders", database="sales")
        call_args = mock_sql.call_args[0][0]
        assert "`orders`" in call_args
        assert "`sales`" in call_args


@patch("pymysql.connect")
def test_load_mysql_table_uses_env_dsn(mock_connect, monkeypatch):
    monkeypatch.setenv("MYSQL_DSN", "mysql://envuser:envpass@envhost:3306/envdb")
    df_expected = pd.DataFrame({"col": [1]})
    with patch("pandas.read_sql", return_value=df_expected):
        mock_connect.return_value = MagicMock()
        mock_connect.return_value.close = MagicMock()
        load_mysql_table(table="t", database="d")
    call_kwargs = mock_connect.call_args[1]
    assert call_kwargs.get("host") == "envhost"
    assert call_kwargs.get("user") == "envuser"

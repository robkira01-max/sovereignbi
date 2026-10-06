"""Tests — app/data/postgres_store.py (Sprint 2)."""
import os
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from app.data.postgres_store import _quote_ident, list_tables, load_table


# ── _quote_ident ──────────────────────────────────────────────────────────────

def test_quote_ident_simple():
    assert _quote_ident("ventes") == '"ventes"'


def test_quote_ident_with_underscore():
    assert _quote_ident("ventes_detail") == '"ventes_detail"'


def test_quote_ident_uppercase_accepted():
    # isalnum() accepte les majuscules — comportement attendu
    result = _quote_ident("Ventes")
    assert result == '"Ventes"'


def test_quote_ident_space_rejected():
    with pytest.raises(ValueError):
        _quote_ident("ventes detail")


def test_quote_ident_semicolon_rejected():
    with pytest.raises(ValueError):
        _quote_ident("ventes; DROP TABLE ventes")


def test_quote_ident_empty_rejected():
    with pytest.raises(ValueError):
        _quote_ident("")


def test_quote_ident_hyphen_rejected():
    with pytest.raises(ValueError):
        _quote_ident("ventes-2026")


# ── Missing DSN ───────────────────────────────────────────────────────────────

def test_load_table_missing_dsn_raises(monkeypatch):
    monkeypatch.delenv("SOVEREIGN_PG_DSN", raising=False)
    with pytest.raises(EnvironmentError, match="SOVEREIGN_PG_DSN"):
        load_table("ventes")


def test_list_tables_missing_dsn_raises(monkeypatch):
    monkeypatch.delenv("SOVEREIGN_PG_DSN", raising=False)
    with pytest.raises(EnvironmentError, match="SOVEREIGN_PG_DSN"):
        list_tables()


# ── Mocked psycopg2 ───────────────────────────────────────────────────────────

def _mock_conn(rows, columns=None):
    """Build a mock psycopg2 connection returning fixed rows."""
    mock_cur = MagicMock()
    mock_cur.__enter__ = lambda s: s
    mock_cur.__exit__ = MagicMock(return_value=False)
    mock_cur.fetchall.return_value = rows
    mock_conn = MagicMock()
    mock_conn.__enter__ = lambda s: s
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value = mock_cur
    return mock_conn, mock_cur


def test_list_tables_returns_names(monkeypatch):
    monkeypatch.setenv("SOVEREIGN_PG_DSN", "postgresql://fake:fake@localhost/fake")
    mock_conn, _ = _mock_conn([("ventes",), ("clients",)])
    with patch("app.data.postgres_store.psycopg2.connect", return_value=mock_conn):
        result = list_tables()
    assert result == ["ventes", "clients"]


def test_list_tables_custom_schema(monkeypatch):
    monkeypatch.setenv("SOVEREIGN_PG_DSN", "postgresql://fake:fake@localhost/fake")
    mock_conn, mock_cur = _mock_conn([("orders",)])
    with patch("app.data.postgres_store.psycopg2.connect", return_value=mock_conn):
        result = list_tables(schema="sales")
    call_args = mock_cur.execute.call_args
    assert "sales" in str(call_args)


def test_load_table_returns_dataframe(monkeypatch):
    monkeypatch.setenv("SOVEREIGN_PG_DSN", "postgresql://fake:fake@localhost/fake")
    df_expected = pd.DataFrame({"id": [1, 2], "montant": [100.0, 200.0]})
    with patch("app.data.postgres_store.psycopg2.connect"), \
         patch("app.data.postgres_store.pd.read_sql", return_value=df_expected) as mock_sql:
        result = load_table("ventes")
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 2


def test_load_table_invalid_name_rejected(monkeypatch):
    monkeypatch.setenv("SOVEREIGN_PG_DSN", "postgresql://fake:fake@localhost/fake")
    with pytest.raises(ValueError):
        load_table("ventes; DROP TABLE ventes")

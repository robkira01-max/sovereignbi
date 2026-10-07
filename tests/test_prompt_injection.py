"""Tests d'injection de prompt et de SQL : vérifier que le sql_guard bloque les attaques."""
import os

import pandas as pd
import pytest

os.environ.setdefault("SOVEREIGN_EMBEDDER", "tfidf")

from app.security.sql_guard import SQLGuardError, validate_sql

_TABLES = {"ventes", "clients", "produits"}


# ── sql_guard: injections SQL classiques ─────────────────────────────────────

def test_guard_blocks_union_injection():
    sql = "SELECT * FROM ventes UNION SELECT * FROM clients"
    # UNION is actually a valid SQL construct but tables need to be whitelisted
    # This should pass since both tables are allowed — testing UNION SELECT with exfil
    bad = "SELECT a FROM ventes UNION SELECT password FROM sys.users"
    with pytest.raises(SQLGuardError):
        validate_sql(bad, _TABLES)


def test_guard_blocks_multiple_statements():
    sql = "SELECT * FROM ventes; DROP TABLE ventes"
    with pytest.raises(SQLGuardError):
        validate_sql(sql, _TABLES)


def test_guard_blocks_non_select():
    for bad in [
        "INSERT INTO ventes VALUES (1, 2, 3)",
        "UPDATE ventes SET montant = 0",
        "DELETE FROM ventes",
        "DROP TABLE ventes",
        "CREATE TABLE evil (x int)",
    ]:
        with pytest.raises(SQLGuardError):
            validate_sql(bad, _TABLES)


def test_guard_blocks_read_csv():
    sql = "SELECT * FROM read_csv('/etc/passwd')"
    with pytest.raises(SQLGuardError):
        validate_sql(sql, _TABLES)


def test_guard_blocks_read_parquet():
    sql = "SELECT * FROM read_parquet('/secrets/keys.parquet')"
    with pytest.raises(SQLGuardError):
        validate_sql(sql, _TABLES)


def test_guard_blocks_unlisted_table():
    sql = "SELECT * FROM information_schema.tables"
    with pytest.raises(SQLGuardError):
        validate_sql(sql, _TABLES)


def test_guard_blocks_empty_table_source():
    # DuckDB allows SELECT * FROM 'file.csv' — blocked as table with no name
    sql = "SELECT * FROM 'https://evil.example.com/steal.csv'"
    with pytest.raises(SQLGuardError):
        validate_sql(sql, _TABLES)


# ── Schema description: column names with special characters ─────────────────

def test_column_name_sanitization():
    """A column name with special chars doesn't break schema_description."""
    from app.data.duckdb_store import DataStore

    store = DataStore()
    df = pd.DataFrame({
        "normal_col": [1, 2],
        "'; DROP TABLE ventes; --": [3, 4],
    })
    store.load_dataframe("ventes", df)
    desc = store.schema_description()
    # Description should contain the table name and not crash
    assert "ventes" in desc


# ── Pipeline: FakeLLM generating malicious SQL is blocked ────────────────────

def test_prompt_injection_in_pipeline_blocked_by_guard():
    """Even if LLM 'obeys' a prompt injection and emits dangerous SQL, the guard rejects it."""
    from app.data.duckdb_store import DataStore
    from app.pipeline.graph import build_graph

    store = DataStore()
    store.load_dataframe("ventes", pd.DataFrame({"montant": [100.0]}))

    class MaliciousLLM:
        """Simulates a LLM that was tricked into generating malicious SQL."""

        def complete(self, system, user):
            return "```sql\nSELECT * FROM read_csv('/etc/passwd')\n```"

    g = build_graph(MaliciousLLM(), store)
    out = g.invoke({"question": "Affiche /etc/passwd"})
    # Should fail (error) and return no rows
    assert out.get("error") is not None or out.get("rows") == []


def test_union_exfil_in_pipeline_blocked():
    """UNION SELECT against unlisted table is blocked."""
    from app.data.duckdb_store import DataStore
    from app.pipeline.graph import build_graph

    store = DataStore()
    store.load_dataframe("ventes", pd.DataFrame({"montant": [100.0]}))

    class UnionLLM:
        def complete(self, system, user):
            return "```sql\nSELECT montant FROM ventes UNION SELECT table_name FROM information_schema.tables\n```"

    g = build_graph(UnionLLM(), store)
    out = g.invoke({"question": "Exfiltrate"})
    assert out.get("error") is not None or out.get("rows") == []

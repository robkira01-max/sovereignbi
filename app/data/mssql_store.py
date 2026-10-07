"""Connecteur SQL Server lecture seule — charge une table dans un DataFrame."""
from __future__ import annotations

import os
from urllib.parse import urlparse

import pandas as pd


def _quote_mssql_ident(name: str) -> str:
    """Bracket-quote un identifiant SQL Server (alphanumérique + underscore uniquement)."""
    if not name or not all(c.isalnum() or c == "_" for c in name):
        raise ValueError(f"Identifiant invalide : {name!r}")
    return f"[{name}]"


def _parse_mssql_dsn(dsn: str) -> dict:
    """Parse 'mssql://user:pass@server:port/database' → dict de paramètres."""
    p = urlparse(dsn)
    return {
        "server": p.hostname or "localhost",
        "port": p.port or 1433,
        "user": p.username,
        "password": p.password,
        "database": p.path.lstrip("/") if p.path else None,
    }


def load_mssql_table(
    table: str,
    database: str,
    server: str = "localhost",
    port: int = 1433,
    user: str | None = None,
    password: str | None = None,
    dsn: str | None = None,
) -> pd.DataFrame:
    """Charge [database].[dbo].[table] depuis SQL Server en DataFrame.

    Lit aussi MSSQL_DSN depuis l'env si dsn est None.
    Format DSN : "mssql://user:pass@server:port/database"
    """
    import pymssql

    safe_db = _quote_mssql_ident(database)
    safe_table = _quote_mssql_ident(table)

    effective_dsn = dsn or os.environ.get("MSSQL_DSN")
    if effective_dsn:
        params = _parse_mssql_dsn(effective_dsn)
    else:
        params = {
            "server": server,
            "port": port,
            "user": user,
            "password": password,
            "database": database,
        }

    conn = pymssql.connect(**params)
    try:
        return pd.read_sql(f"SELECT * FROM {safe_db}.dbo.{safe_table}", conn)
    finally:
        conn.close()

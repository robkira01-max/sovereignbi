"""Connecteur MySQL lecture seule — charge une table dans un DataFrame."""
from __future__ import annotations

import os
from urllib.parse import urlparse

import pandas as pd


def _quote_mysql_ident(name: str) -> str:
    """Backtick-quote un identifiant MySQL (alphanumérique + underscore uniquement)."""
    if not name or not all(c.isalnum() or c == "_" for c in name):
        raise ValueError(f"Identifiant invalide : {name!r}")
    return f"`{name}`"


def _parse_mysql_dsn(dsn: str) -> dict:
    """Parse 'mysql://user:pass@host:port/db' → dict de paramètres de connexion."""
    p = urlparse(dsn)
    return {
        "host": p.hostname or "localhost",
        "port": p.port or 3306,
        "user": p.username,
        "password": p.password,
        "database": p.path.lstrip("/") if p.path else None,
    }


def load_mysql_table(
    table: str,
    database: str,
    host: str = "localhost",
    port: int = 3306,
    user: str | None = None,
    password: str | None = None,
    dsn: str | None = None,
) -> pd.DataFrame:
    """Charge `database`.`table` depuis MySQL en DataFrame.

    Si dsn est fourni (ex: "mysql://user:pass@host:port/db"), il prend la priorité.
    Sinon, utilise host/port/user/password/database.
    Lit aussi MYSQL_DSN depuis l'env si dsn est None.
    """
    import pymysql

    safe_db = _quote_mysql_ident(database)
    safe_table = _quote_mysql_ident(table)

    effective_dsn = dsn or os.environ.get("MYSQL_DSN")
    if effective_dsn:
        params = _parse_mysql_dsn(effective_dsn)
    else:
        params = {
            "host": host,
            "port": port,
            "user": user,
            "password": password,
            "database": database,
        }

    conn = pymysql.connect(**params)
    try:
        return pd.read_sql(f"SELECT * FROM {safe_db}.{safe_table}", conn)
    finally:
        conn.close()

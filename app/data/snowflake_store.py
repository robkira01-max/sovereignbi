"""Connecteur Snowflake lecture seule — charge une table dans un DataFrame."""
from __future__ import annotations

import pandas as pd


def _quote_sf_ident(name: str) -> str:
    if not name or not all(c.isalnum() or c == "_" for c in name):
        raise ValueError(f"Identifiant invalide : {name!r}")
    return f'"{name}"'


def load_snowflake_table(
    table: str,
    database: str,
    schema: str = "PUBLIC",
    account: str | None = None,
    user: str | None = None,
    password: str | None = None,
    warehouse: str | None = None,
    dsn: str | None = None,
    limit: int = 50_000,
) -> pd.DataFrame:
    """Charge database.schema.table depuis Snowflake en DataFrame (max *limit* lignes)."""
    try:
        import snowflake.connector  # type: ignore[import]
    except ImportError as exc:
        raise ImportError(
            "snowflake-connector-python requis : pip install snowflake-connector-python"
        ) from exc

    if dsn:
        from urllib.parse import urlparse
        p = urlparse(dsn)
        account = account or (p.hostname or "")
        user = user or p.username
        password = password or p.password
        database = database or p.path.lstrip("/")

    conn = snowflake.connector.connect(
        account=account,
        user=user,
        password=password,
        database=database,
        schema=schema,
        warehouse=warehouse,
    )
    try:
        tbl = f"{_quote_sf_ident(database)}.{_quote_sf_ident(schema)}.{_quote_sf_ident(table)}"
        with conn.cursor() as cur:
            cur.execute(f"SELECT * FROM {tbl} LIMIT {int(limit)}")
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
        return pd.DataFrame(rows, columns=cols)
    finally:
        conn.close()

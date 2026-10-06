"""Connecteur PostgreSQL en lecture seule.

Utilisation : la chaîne de connexion vient UNIQUEMENT d'une variable d'environnement
(SOVEREIGN_PG_DSN). Jamais codée en dur. L'utilisateur DB doit avoir uniquement
des droits SELECT sur les schémas autorisés.
"""
import os

import psycopg2
import pandas as pd


_ENV_VAR = "SOVEREIGN_PG_DSN"


def _get_dsn() -> str:
    dsn = os.environ.get(_ENV_VAR, "")
    if not dsn:
        raise EnvironmentError(
            f"Variable d'environnement {_ENV_VAR!r} non définie. "
            "Exemple : postgresql://readonly_user:pwd@host:5432/mydb"
        )
    return dsn


def load_table(name: str, schema: str = "public", dsn: str | None = None) -> pd.DataFrame:
    """Charge une table PostgreSQL dans un DataFrame pandas (lecture seule)."""
    safe_schema = _quote_ident(schema)
    safe_table = _quote_ident(name)
    conn_str = dsn or _get_dsn()
    with psycopg2.connect(conn_str) as conn:
        return pd.read_sql(f"SELECT * FROM {safe_schema}.{safe_table}", conn)


def list_tables(schema: str = "public", dsn: str | None = None) -> list[str]:
    """Liste les tables accessibles dans le schéma."""
    conn_str = dsn or _get_dsn()
    with psycopg2.connect(conn_str) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = %s AND table_type = 'BASE TABLE' "
                "ORDER BY table_name",
                (schema,),
            )
            return [row[0] for row in cur.fetchall()]


def _quote_ident(name: str) -> str:
    """Échappe un identifiant PostgreSQL (protection contre l'injection SQL)."""
    if not name or not all(c.isalnum() or c in ("_",) for c in name):
        raise ValueError(f"Nom d'identifiant invalide : {name!r}")
    return f'"{name}"'

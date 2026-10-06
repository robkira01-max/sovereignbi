"""Tile renderer — always routes through sql_guard before execution."""
from __future__ import annotations

from app.dashboards.models import Tile
from app.data.duckdb_store import DataStore
from app.security.sql_guard import SQLGuardError, validate_sql


def render_tile(tile: Tile, store: DataStore) -> dict:
    """Execute a pinned-SQL tile and return {columns, rows, error}.

    A metric-only tile (no sql_pinned) returns an error; the caller is
    responsible for building the SQL from the metric definition first.
    Every SQL path goes through validate_sql — no bypass is possible.
    """
    sql = tile.sql_pinned
    if sql is None:
        return {"columns": [], "rows": [], "error": "Tuile sans SQL épinglé"}

    try:
        safe = validate_sql(sql, store.tables)
    except SQLGuardError as e:
        return {"columns": [], "rows": [], "error": str(e)}
    except Exception as e:
        return {"columns": [], "rows": [], "error": f"Erreur de validation : {e}"}

    try:
        cols, rows = store.execute(safe)
        return {"columns": cols, "rows": rows, "error": None}
    except Exception as e:
        return {"columns": [], "rows": [], "error": str(e)}

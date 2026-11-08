"""Tile renderer — always routes through sql_guard before execution."""
from __future__ import annotations

import re

from app.dashboards.models import Tile
from app.data.duckdb_store import DataStore
from app.security.sql_guard import SQLGuardError, validate_sql

# Strictly safe column name: letters/digits/underscore only, cannot start with digit
_COL_RE = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

# Region name: printable chars, no SQL metacharacters
_REGION_MAX = 120


def render_tile(
    tile: Tile,
    store: DataStore,
    region: str | None = None,
    region_col: str | None = None,
) -> dict:
    """Execute a pinned-SQL tile and return {columns, rows, error}.

    Optional region filter: wraps the validated SQL in a subquery and adds
    a WHERE clause on the region column.  Falls back to unfiltered data if
    the column does not exist in the result (e.g. aggregate KPI tiles).
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

    if region:
        # Determine region column: explicit param > tile option > default "region"
        tile_col = (tile.options or {}).get("region_col") if tile.options else None
        col = region_col or tile_col or "region"

        if not _COL_RE.match(col):
            # Unsafe column name — fall through to unfiltered
            pass
        elif len(region) > _REGION_MAX or "'" in region.replace("''", ""):
            pass
        else:
            region_esc = region.replace("'", "''")
            filtered_sql = (
                f"SELECT * FROM ({safe}) AS _sub"
                f" WHERE _sub.{col} = '{region_esc}'"
            )
            try:
                cols, rows = store.execute(filtered_sql)
                return {"columns": cols, "rows": rows, "error": None, "region": region}
            except Exception:
                # Column absent or type mismatch — fall through to unfiltered result
                pass

    try:
        cols, rows = store.execute(safe)
        return {"columns": cols, "rows": rows, "error": None}
    except Exception as e:
        return {"columns": [], "rows": [], "error": str(e)}

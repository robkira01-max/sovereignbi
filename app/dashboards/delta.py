"""Sparkline and period-over-period delta computation for KPI tiles."""
from __future__ import annotations

import re
from typing import Any

_DATE_RE = re.compile(
    r'\b(date|year|annee|mois|month|periode|period|time|datetime|day|jour|week|semaine)\b',
    re.IGNORECASE,
)
_PERIOD_MAX_POINTS: dict[str, int] = {"mom": 12, "yoy": 5, "wow": 10}


def _detect_date_col(columns: list[str]) -> str | None:
    for col in columns:
        if _DATE_RE.search(col):
            return col
    return None


def _detect_numeric_col(columns: list[str], skip: str | None) -> str | None:
    for col in columns:
        if col != skip:
            return col
    return None


def compute_delta(sql: str, store: Any, period: str = "mom") -> dict:
    """Execute *sql*, detect date + numeric columns, return delta and sparkline.

    Returns a dict with keys:
      current, previous, delta_abs, delta_pct, direction (up|down|flat|None),
      sparkline_points, date_col, num_col
    or {"error": "...message..."} on failure.
    """
    if period not in _PERIOD_MAX_POINTS:
        period = "mom"

    try:
        cols, rows = store.execute(sql.rstrip(";"))
    except Exception as exc:
        return {"error": str(exc)}

    if not rows or not cols:
        return {"error": "Pas de données."}

    date_col = _detect_date_col(cols)
    num_col = _detect_numeric_col(cols, date_col)
    if num_col is None:
        return {"error": "Aucune colonne numérique trouvée."}

    num_idx = cols.index(num_col)
    date_idx = cols.index(date_col) if date_col is not None else None

    try:
        sorted_rows = (
            sorted(rows, key=lambda r: str(r[date_idx]))
            if date_idx is not None
            else list(rows)
        )
    except Exception:
        sorted_rows = list(rows)

    max_pts = _PERIOD_MAX_POINTS[period]
    sparkline_rows = sorted_rows[-max_pts:]

    try:
        vals = [
            float(r[num_idx])
            for r in sparkline_rows
            if r[num_idx] is not None
        ]
    except (TypeError, ValueError):
        return {"error": "Colonne numérique non convertible en float."}

    if not vals:
        return {"error": "Pas de valeurs numériques."}

    current = vals[-1]
    previous = vals[-2] if len(vals) >= 2 else None

    delta_abs: float | None = None
    delta_pct: float | None = None
    direction: str | None = None

    if previous is not None:
        delta_abs = current - previous
        if previous != 0:
            delta_pct = round(delta_abs / abs(previous) * 100, 2)
        direction = "up" if delta_abs > 0 else ("down" if delta_abs < 0 else "flat")

    return {
        "current": current,
        "previous": previous,
        "delta_abs": round(delta_abs, 4) if delta_abs is not None else None,
        "delta_pct": delta_pct,
        "direction": direction,
        "sparkline_points": vals,
        "date_col": date_col,
        "num_col": num_col,
    }

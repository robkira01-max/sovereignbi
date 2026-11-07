"""Threshold (traffic-light) evaluation for KPI tiles.

A threshold list is stored in Tile.options["thresholds"] as a list of dicts:
  [
    {"op": ">=", "value": 30, "color": "#ef4444", "label": "Critique"},
    {"op": ">=", "value": 20, "color": "#f59e0b", "label": "Élevé"},
    {"color": "#22c55e", "label": "Normal"},          ← default (no op/value)
  ]

Rules:
- Thresholds are tested in list order; the first match wins.
- An entry without "op"/"value" is the default fallback.
- Supported ops: ">", ">=", "<", "<=", "==", "!=".
- If no threshold matches and no default is defined, returns None.
"""
from __future__ import annotations

_OPS = {
    ">":  lambda v, t: v > t,
    ">=": lambda v, t: v >= t,
    "<":  lambda v, t: v < t,
    "<=": lambda v, t: v <= t,
    "==": lambda v, t: v == t,
    "!=": lambda v, t: v != t,
}

DEFAULT_COLOR = "#6b7280"  # neutral grey


def evaluate_threshold(
    value: float,
    thresholds: list[dict],
) -> dict:
    """Return {color, label, matched} for the first matching threshold.

    *value*  : numeric value to compare.
    *thresholds*: list of threshold dicts (see module docstring).
    Returns {"color": str, "label": str | None, "matched": bool}.
    """
    for t in thresholds:
        op = t.get("op", "")
        tval = t.get("value")

        if op and tval is not None:
            fn = _OPS.get(op)
            if fn is None:
                continue
            try:
                if fn(value, float(tval)):
                    return {
                        "color": t.get("color", DEFAULT_COLOR),
                        "label": t.get("label"),
                        "matched": True,
                    }
            except (TypeError, ValueError):
                continue
        else:
            # Default / fallback entry (no op or value)
            return {
                "color": t.get("color", DEFAULT_COLOR),
                "label": t.get("label"),
                "matched": True,
            }
    return {"color": DEFAULT_COLOR, "label": None, "matched": False}

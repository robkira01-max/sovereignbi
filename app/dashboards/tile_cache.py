"""Simple in-memory tile execution timestamp tracker.

Records when each tile was last executed so the /freshness endpoint
can report data age without modifying the /data response.
"""
from __future__ import annotations

from datetime import datetime, timezone

_LAST_EXECUTED: dict[str, datetime] = {}


def record_execution(dashboard_id: str, tile_id: str) -> None:
    """Mark tile as executed right now."""
    _LAST_EXECUTED[f"{dashboard_id}:{tile_id}"] = datetime.now(timezone.utc)


def age_seconds(dashboard_id: str, tile_id: str) -> float | None:
    """Return seconds since last execution, or None if never executed."""
    ts = _LAST_EXECUTED.get(f"{dashboard_id}:{tile_id}")
    if ts is None:
        return None
    return (datetime.now(timezone.utc) - ts).total_seconds()


def clear_all() -> None:
    """Clear all recorded timestamps (useful in tests)."""
    _LAST_EXECUTED.clear()

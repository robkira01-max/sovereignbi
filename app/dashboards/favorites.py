"""Per-user dashboard favorites stored in data/favorites.json.

Key: SHA-256 hex of the raw API key (never store the key itself).
Value: sorted list of dashboard IDs marked as favorites.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

_FAVORITES_PATH = Path("data/favorites.json")


def _load(path: Path | None = None) -> dict[str, list[str]]:
    p = path if path is not None else _FAVORITES_PATH
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save(data: dict[str, list[str]], path: Path | None = None) -> None:
    p = path if path is not None else _FAVORITES_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _key_hash(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()


def toggle_favorite(api_key: str, dashboard_id: str, path: Path | None = None) -> bool:
    """Add or remove dashboard_id from favorites. Returns True if now favorited."""
    data = _load(path)
    h = _key_hash(api_key)
    favs = data.get(h, [])
    if dashboard_id in favs:
        favs.remove(dashboard_id)
        is_fav = False
    else:
        favs.append(dashboard_id)
        is_fav = True
    data[h] = sorted(favs)
    _save(data, path)
    return is_fav


def get_favorites(api_key: str, path: Path | None = None) -> list[str]:
    """Return the list of favorited dashboard IDs for this user."""
    data = _load(path)
    return data.get(_key_hash(api_key), [])

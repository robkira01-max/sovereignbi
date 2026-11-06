"""Generate a one-sentence AI insight for a tile's data result."""
from __future__ import annotations

import hashlib
import time
from typing import Optional

_CACHE: dict[str, tuple[str, float]] = {}
_TTL = 900  # 15 minutes


def _key(tile_id: str, sql: str) -> str:
    return hashlib.md5(f"{tile_id}::{sql}".encode()).hexdigest()


def get_cached(tile_id: str, sql: str) -> Optional[str]:
    entry = _CACHE.get(_key(tile_id, sql))
    if entry is None:
        return None
    text, ts = entry
    if time.monotonic() - ts > _TTL:
        _CACHE.pop(_key(tile_id, sql), None)
        return None
    return text


def set_cached(tile_id: str, sql: str, text: str) -> None:
    _CACHE[_key(tile_id, sql)] = (text, time.monotonic())


def _format_data(columns: list[str], rows: list, max_rows: int = 20) -> str:
    if not columns or not rows:
        return "(pas de données)"
    lines = [" | ".join(columns)]
    for row in rows[:max_rows]:
        lines.append(" | ".join(str(v) for v in row))
    if len(rows) > max_rows:
        lines.append(f"… ({len(rows) - max_rows} lignes de plus)")
    return "\n".join(lines)


def build_prompt(title: str, columns: list[str], rows: list) -> str:
    return (
        f"Données : {title}\n"
        f"{_format_data(columns, rows)}\n\n"
        "En une seule phrase courte en français, formule l'observation la plus importante "
        "ou la plus surprenante. Cite des chiffres précis si pertinent. "
        "Pas d'introduction, pas de markdown, juste la phrase."
    )


def generate_insight(title: str, columns: list[str], rows: list, llm) -> str:
    """Call the LLM and return one insight sentence."""
    prompt = build_prompt(title, columns, rows)
    return llm.complete(
        system=(
            "Tu es un analyste de données spécialisé en statistiques publiques. "
            "Réponds toujours en une seule phrase, en français, sans introduction."
        ),
        user=prompt,
    ).strip().split("\n")[0]  # only first line in case the LLM adds extras

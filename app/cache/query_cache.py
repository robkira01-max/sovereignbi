"""LRU cache pour les réponses SQL — évite les appels LLM répétitifs."""
from __future__ import annotations

import hashlib
import json
import threading
import time
from collections import OrderedDict
from typing import Any

DEFAULT_MAX_SIZE = 256
DEFAULT_TTL_SECONDS = 3600


class QueryCache:
    """Thread-safe LRU cache with TTL for SQL query results."""

    def __init__(self, max_size: int = DEFAULT_MAX_SIZE, ttl: int = DEFAULT_TTL_SECONDS) -> None:
        self.max_size = max_size
        self.ttl = ttl
        self._store: OrderedDict[str, tuple[dict, float]] = OrderedDict()
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def _make_key(self, question: str, table_names: frozenset[str]) -> str:
        payload = json.dumps(
            {"q": question.strip().lower(), "tables": sorted(table_names)},
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    def get(self, question: str, table_names: frozenset[str]) -> dict | None:
        key = self._make_key(question, table_names)
        with self._lock:
            if key not in self._store:
                self._misses += 1
                return None
            value, expires_at = self._store[key]
            if time.monotonic() > expires_at:
                del self._store[key]
                self._misses += 1
                return None
            self._store.move_to_end(key)
            self._hits += 1
            return value

    def set(self, question: str, table_names: frozenset[str], value: dict) -> None:
        key = self._make_key(question, table_names)
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
            self._store[key] = (value, time.monotonic() + self.ttl)
            while len(self._store) > self.max_size:
                self._store.popitem(last=False)

    def invalidate(self) -> int:
        with self._lock:
            count = len(self._store)
            self._store.clear()
            return count

    def stats(self) -> dict[str, Any]:
        with self._lock:
            total = self._hits + self._misses
            return {
                "size": len(self._store),
                "max_size": self.max_size,
                "ttl_seconds": self.ttl,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(self._hits / total, 3) if total else 0.0,
            }

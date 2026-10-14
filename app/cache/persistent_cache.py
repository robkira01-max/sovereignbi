"""SQLite-backed persistent query cache.

Extends QueryCache with disk persistence so cached results survive restarts.
Set CACHE_SQLITE_PATH to a file path (default: data/query_cache.sqlite).
Use ':memory:' or leave unset to get an in-memory-only QueryCache.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from pathlib import Path

from app.cache.query_cache import QueryCache


_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS query_cache (
    key      TEXT    PRIMARY KEY,
    value_json TEXT  NOT NULL,
    expires_at REAL  NOT NULL
);
"""

_PURGE_EXPIRED = "DELETE FROM query_cache WHERE expires_at < ?"
_UPSERT = """
INSERT INTO query_cache (key, value_json, expires_at)
VALUES (?, ?, ?)
ON CONFLICT(key) DO UPDATE SET
    value_json = excluded.value_json,
    expires_at = excluded.expires_at;
"""
_SELECT_ONE = "SELECT value_json, expires_at FROM query_cache WHERE key = ?"
_DELETE = "DELETE FROM query_cache WHERE key = ?"
_SELECT_ALL_VALID = "SELECT key, value_json, expires_at FROM query_cache WHERE expires_at > ?"
_DELETE_ALL = "DELETE FROM query_cache"
_COUNT = "SELECT COUNT(*) FROM query_cache"


class PersistentQueryCache(QueryCache):
    """QueryCache with SQLite write-through persistence."""

    def __init__(
        self,
        db_path: str | None = None,
        max_size: int = 256,
        ttl: int = 3600,
    ) -> None:
        super().__init__(max_size=max_size, ttl=ttl)
        resolved = db_path or os.environ.get("CACHE_SQLITE_PATH", "data/query_cache.sqlite")
        self._db_path = resolved
        self._db_lock = threading.Lock()

        if resolved != ":memory:":
            Path(resolved).parent.mkdir(parents=True, exist_ok=True)

        self._db = sqlite3.connect(resolved, check_same_thread=False)
        self._db.execute(_CREATE_TABLE)
        self._db.commit()
        self._load_from_db()

    def _conn_execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        with self._db_lock:
            return self._db.execute(sql, params)

    def _load_from_db(self) -> None:
        """Warm the in-memory LRU from SQLite on startup."""
        now = time.monotonic()
        rows = self._conn_execute(_SELECT_ALL_VALID, (time.time(),)).fetchall()
        for key, value_json, expires_at in rows:
            try:
                value = json.loads(value_json)
            except (json.JSONDecodeError, TypeError):
                continue
            # Translate stored wall-clock expires_at to monotonic offset
            remaining = expires_at - time.time()
            if remaining > 0:
                with self._lock:
                    self._store[key] = (value, now + remaining)

    def set(self, question: str, table_names: frozenset[str], value: dict) -> None:
        super().set(question, table_names, value)
        key = self._make_key(question, table_names)
        expires_wall = time.time() + self.ttl
        try:
            with self._db_lock:
                self._db.execute(_UPSERT, (key, json.dumps(value), expires_wall))
                self._db.commit()
        except Exception:
            pass  # SQLite errors must not disrupt the hot path

    def get(self, question: str, table_names: frozenset[str]) -> dict | None:
        # Try in-memory first (fast path)
        result = super().get(question, table_names)
        if result is not None:
            return result

        # Fallback to SQLite (cache warm-up after restart)
        key = self._make_key(question, table_names)
        try:
            row = self._conn_execute(_SELECT_ONE, (key,)).fetchone()
        except Exception:
            return None
        if row is None:
            return None
        value_json, expires_wall = row
        if time.time() > expires_wall:
            try:
                self._conn_execute(_DELETE, (key,))
                with self._db_lock:
                    self._db.commit()
            except Exception:
                pass
            return None
        try:
            value = json.loads(value_json)
        except (json.JSONDecodeError, TypeError):
            return None
        # Promote back into memory
        remaining = expires_wall - time.time()
        with self._lock:
            self._store[key] = (value, time.monotonic() + remaining)
            self._hits += 1
        return value

    def invalidate(self) -> int:
        count = super().invalidate()
        try:
            with self._db_lock:
                self._db.execute(_DELETE_ALL)
                self._db.commit()
        except Exception:
            pass
        return count

    def prune_expired(self) -> int:
        """Remove expired rows from SQLite. Call periodically."""
        try:
            cur = self._conn_execute(_PURGE_EXPIRED, (time.time(),))
            with self._db_lock:
                self._db.commit()
            return cur.rowcount
        except Exception:
            return 0

    def db_size(self) -> int:
        try:
            row = self._conn_execute(_COUNT).fetchone()
            return row[0] if row else 0
        except Exception:
            return 0

    def stats(self) -> dict:
        base = super().stats()
        base["sqlite_path"] = self._db_path
        base["sqlite_rows"] = self.db_size()
        return base

    def close(self) -> None:
        try:
            with self._db_lock:
                self._db.close()
        except Exception:
            pass

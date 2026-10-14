"""Tests for Sprint H4 — SQLite persistent cache."""
import tempfile
import time
from pathlib import Path

import pytest

from app.cache.persistent_cache import PersistentQueryCache


@pytest.fixture
def tmp_db(tmp_path):
    return str(tmp_path / "test_cache.sqlite")


def test_set_and_get(tmp_db):
    c = PersistentQueryCache(db_path=tmp_db)
    c.set("q1", frozenset({"t"}), {"answer": "42"})
    assert c.get("q1", frozenset({"t"})) == {"answer": "42"}
    c.close()


def test_persists_across_instances(tmp_db):
    c1 = PersistentQueryCache(db_path=tmp_db)
    c1.set("q2", frozenset({"sales"}), {"answer": "100"})
    c1.close()

    c2 = PersistentQueryCache(db_path=tmp_db)
    result = c2.get("q2", frozenset({"sales"}))
    assert result == {"answer": "100"}
    c2.close()


def test_miss_returns_none(tmp_db):
    c = PersistentQueryCache(db_path=tmp_db)
    assert c.get("unknown", frozenset({"t"})) is None
    c.close()


def test_invalidate_clears_db(tmp_db):
    c = PersistentQueryCache(db_path=tmp_db)
    c.set("a", frozenset({"t"}), {"x": 1})
    c.set("b", frozenset({"t"}), {"x": 2})
    c.invalidate()
    assert c.db_size() == 0
    c.close()


def test_stats_includes_sqlite_fields(tmp_db):
    c = PersistentQueryCache(db_path=tmp_db)
    stats = c.stats()
    assert "sqlite_path" in stats
    assert "sqlite_rows" in stats
    c.close()


def test_sqlite_rows_increments(tmp_db):
    c = PersistentQueryCache(db_path=tmp_db)
    c.set("qa", frozenset({"t"}), {"v": 1})
    c.set("qb", frozenset({"t"}), {"v": 2})
    assert c.db_size() == 2
    c.close()


def test_ttl_expiry_in_db(tmp_db):
    c = PersistentQueryCache(db_path=tmp_db, ttl=1)
    c.set("expire", frozenset({"t"}), {"v": "x"})
    time.sleep(1.2)
    assert c.get("expire", frozenset({"t"})) is None
    c.close()


def test_prune_removes_expired(tmp_db):
    c = PersistentQueryCache(db_path=tmp_db, ttl=1)
    c.set("prune_me", frozenset({"t"}), {"v": 1})
    time.sleep(1.2)
    removed = c.prune_expired()
    assert removed >= 1
    c.close()


def test_memory_first_hit(tmp_db):
    c = PersistentQueryCache(db_path=tmp_db)
    tables = frozenset({"t"})
    c.set("hot", tables, {"v": 7})
    # Second get should be served from memory (stats hit)
    c.get("hot", tables)
    stats = c.stats()
    assert stats["hits"] >= 1
    c.close()


def test_warm_reload_increments_hits(tmp_db):
    """After restart, reading from SQLite should populate memory."""
    c1 = PersistentQueryCache(db_path=tmp_db)
    c1.set("warm", frozenset({"t"}), {"v": 99})
    c1.close()

    c2 = PersistentQueryCache(db_path=tmp_db)
    # On first get, it's served from in-memory LRU (loaded at __init__)
    result = c2.get("warm", frozenset({"t"}))
    assert result == {"v": 99}
    c2.close()


def test_memory_path_not_overwritten(tmp_db):
    """':memory:' path should not write a file."""
    c = PersistentQueryCache(db_path=":memory:")
    c.set("x", frozenset(), {"k": 1})
    assert c.get("x", frozenset()) == {"k": 1}
    assert not Path("memory").exists()
    c.close()

"""Tests cache LRU + performance — Sprint 17."""
import time
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app, store, query_cache
from app.cache.query_cache import QueryCache

VIEWER = {"X-Api-Key": "test-viewer-key-s6"}
ADMIN = {"X-Api-Key": "test-admin-key-sprint3"}


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset():
    store.tables.clear()
    query_cache.invalidate()
    yield


# --- QueryCache unit tests ---

def test_cache_set_and_get():
    c = QueryCache(max_size=10)
    tables = frozenset({"sales"})
    c.set("how many?", tables, {"answer": "42"})
    result = c.get("how many?", tables)
    assert result == {"answer": "42"}


def test_cache_miss_returns_none():
    c = QueryCache()
    assert c.get("unknown", frozenset({"t"})) is None


def test_cache_key_normalizes_question():
    c = QueryCache()
    tables = frozenset({"t"})
    c.set("  HOW MANY?  ", tables, {"answer": "1"})
    assert c.get("how many?", tables) == {"answer": "1"}


def test_cache_miss_different_tables():
    c = QueryCache()
    c.set("count", frozenset({"sales"}), {"answer": "5"})
    assert c.get("count", frozenset({"orders"})) is None


def test_cache_ttl_expiry():
    c = QueryCache(ttl=1)
    tables = frozenset({"t"})
    c.set("q", tables, {"answer": "x"})
    time.sleep(1.1)
    assert c.get("q", tables) is None


def test_cache_lru_eviction():
    c = QueryCache(max_size=3)
    for i in range(4):
        c.set(f"q{i}", frozenset({"t"}), {"answer": str(i)})
    assert c.get("q0", frozenset({"t"})) is None
    assert c.get("q3", frozenset({"t"})) is not None


def test_cache_invalidate():
    c = QueryCache()
    c.set("q1", frozenset({"t"}), {"answer": "1"})
    c.set("q2", frozenset({"t"}), {"answer": "2"})
    count = c.invalidate()
    assert count == 2
    assert c.get("q1", frozenset({"t"})) is None


def test_cache_stats():
    c = QueryCache(max_size=10)
    tables = frozenset({"t"})
    c.set("q", tables, {"answer": "x"})
    c.get("q", tables)
    c.get("missing", tables)
    stats = c.stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["hit_rate"] == 0.5
    assert stats["size"] == 1


def test_cache_thread_safety():
    import threading
    c = QueryCache(max_size=100)
    tables = frozenset({"t"})
    errors = []

    def writer():
        for i in range(50):
            try:
                c.set(f"q{i}", tables, {"n": i})
            except Exception as e:
                errors.append(e)

    def reader():
        for i in range(50):
            try:
                c.get(f"q{i}", tables)
            except Exception as e:
                errors.append(e)

    threads = [threading.Thread(target=writer), threading.Thread(target=reader)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []


# --- Route tests ---

def test_cache_stats_route(client):
    r = client.get("/cache/stats", headers=VIEWER)
    assert r.status_code == 200
    data = r.json()
    assert "hits" in data
    assert "misses" in data
    assert "hit_rate" in data
    assert "size" in data


def test_cache_invalidate_route(client):
    r = client.delete("/cache", headers=ADMIN)
    assert r.status_code == 200
    assert "invalidated" in r.json()


def test_cache_invalidate_requires_admin(client):
    r = client.delete("/cache", headers=VIEWER)
    assert r.status_code == 403


def test_x_response_time_header(client):
    r = client.get("/health")
    assert "x-response-time" in r.headers
    assert r.headers["x-response-time"].endswith("ms")


def test_upload_invalidates_cache(client):
    import io
    query_cache.set("q", frozenset(), {"answer": "old"})
    assert query_cache.stats()["size"] == 1
    csv = b"x,y\n1,2\n"
    files = {"file": ("d.csv", io.BytesIO(csv), "text/csv")}
    client.post("/upload", files=files, headers=VIEWER)
    assert query_cache.stats()["size"] == 0

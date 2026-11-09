"""Tests for the sparkline/delta computation and /dashboards/{id}/tiles/{id}/delta route."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("SOVEREIGN_EMBEDDER", "tfidf")

VIEWER = {"X-Api-Key": "test-viewer-key-s6"}
_DASH_ID = "test-delta-dash"


# ── Unit tests for compute_delta ─────────────────────────────────────────────

class _MockStore:
    def __init__(self, cols, rows):
        self._cols = cols
        self._rows = rows

    def execute(self, _sql):
        return self._cols, self._rows


def test_delta_basic_up():
    from app.dashboards.delta import compute_delta
    store = _MockStore(["valeur"], [(10,), (12,), (15,)])
    r = compute_delta("SELECT valeur FROM t", store)
    assert r["current"] == 15
    assert r["previous"] == 12
    assert r["direction"] == "up"
    assert r["delta_pct"] == pytest.approx(25.0, abs=0.1)
    assert r["sparkline_points"] == [10, 12, 15]


def test_delta_basic_down():
    from app.dashboards.delta import compute_delta
    store = _MockStore(["valeur"], [(20,), (15,), (10,)])
    r = compute_delta("SELECT valeur FROM t", store)
    assert r["direction"] == "down"
    assert r["delta_abs"] == pytest.approx(-5.0)


def test_delta_flat():
    from app.dashboards.delta import compute_delta
    store = _MockStore(["valeur"], [(5,), (5,), (5,)])
    r = compute_delta("SELECT valeur FROM t", store)
    assert r["direction"] == "flat"
    assert r["delta_abs"] == pytest.approx(0.0)


def test_delta_with_date_col():
    from app.dashboards.delta import compute_delta
    store = _MockStore(["date", "valeur"], [("2024-01", 10), ("2024-03", 20), ("2024-02", 15)])
    r = compute_delta("SELECT date, valeur FROM t", store)
    assert r["date_col"] == "date"
    assert r["current"] == 20
    assert r["sparkline_points"] == [10, 15, 20]  # sorted by date


def test_delta_single_value():
    from app.dashboards.delta import compute_delta
    store = _MockStore(["valeur"], [(42,)])
    r = compute_delta("SELECT valeur FROM t", store)
    assert r["current"] == 42
    assert r["previous"] is None
    assert r["direction"] is None


def test_delta_no_data():
    from app.dashboards.delta import compute_delta
    store = _MockStore(["valeur"], [])
    r = compute_delta("SELECT valeur FROM t", store)
    assert "error" in r


def test_delta_no_numeric_col():
    from app.dashboards.delta import compute_delta
    # Only a date column → no numeric col after skipping
    store = _MockStore(["date"], [("2024-01",), ("2024-02",)])
    r = compute_delta("SELECT date FROM t", store)
    assert "error" in r


def test_delta_period_yoy_max5():
    from app.dashboards.delta import compute_delta
    rows = [(i,) for i in range(1, 10)]  # 9 rows
    store = _MockStore(["valeur"], rows)
    r = compute_delta("SELECT valeur FROM t", store, period="yoy")
    assert len(r["sparkline_points"]) == 5
    assert r["sparkline_points"][-1] == 9


def test_delta_previous_zero():
    """Zero previous value: delta_abs computed but delta_pct is None."""
    from app.dashboards.delta import compute_delta
    store = _MockStore(["valeur"], [(0,), (5,)])
    r = compute_delta("SELECT valeur FROM t", store)
    assert r["current"] == 5
    assert r["previous"] == 0
    assert r["delta_pct"] is None
    assert r["direction"] == "up"


# ── Route tests ───────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


def _make_dashboard(tmp_path: Path, dash_id: str, sql: str) -> Path:
    import yaml
    data = {
        "id": dash_id,
        "title": "Test Delta",
        "scope": "personal",
        "tiles": [{"id": "kpi1", "type": "kpi", "title": "KPI", "sql_pinned": sql}],
        "theme": {"primary_color": "#1f77b4", "font": "sans-serif", "logo_url": ""},
        "created_at": "", "updated_at": "",
    }
    p = tmp_path / f"{dash_id}.yaml"
    p.write_text(yaml.safe_dump(data, allow_unicode=True))
    return p


def test_delta_route_missing_dashboard(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    r = client.get("/dashboards/ghost/tiles/kpi1/delta", headers=VIEWER)
    assert r.status_code == 404


def test_delta_route_missing_tile(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    _make_dashboard(tmp_path, "d-delta-t1", "SELECT 1 AS v")
    r = client.get("/dashboards/d-delta-t1/tiles/ghost/delta", headers=VIEWER)
    assert r.status_code == 404


def test_delta_route_no_sql(client, tmp_path, monkeypatch):
    import yaml
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    data = {
        "id": "d-nosql", "title": "T", "scope": "personal",
        "tiles": [{"id": "k1", "type": "kpi", "title": "K1"}],
        "theme": {"primary_color": "#000", "font": "sans-serif", "logo_url": ""},
        "created_at": "", "updated_at": "",
    }
    (tmp_path / "d-nosql.yaml").write_text(yaml.safe_dump(data, allow_unicode=True))
    r = client.get("/dashboards/d-nosql/tiles/k1/delta", headers=VIEWER)
    assert r.status_code == 422

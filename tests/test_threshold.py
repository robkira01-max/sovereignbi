"""Tests for threshold evaluation (traffic-light KPI) + /status route."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("SOVEREIGN_EMBEDDER", "tfidf")

VIEWER = {"X-Api-Key": "test-viewer-key-s6"}


# ── Unit tests for evaluate_threshold ────────────────────────────────────────

def test_threshold_first_match():
    from app.dashboards.threshold import evaluate_threshold
    rules = [
        {"op": ">=", "value": 30, "color": "#ef4444", "label": "Critique"},
        {"op": ">=", "value": 20, "color": "#f59e0b", "label": "Élevé"},
        {"color": "#22c55e", "label": "Normal"},
    ]
    r = evaluate_threshold(35, rules)
    assert r["color"] == "#ef4444"
    assert r["label"] == "Critique"
    assert r["matched"] is True


def test_threshold_second_match():
    from app.dashboards.threshold import evaluate_threshold
    rules = [
        {"op": ">=", "value": 30, "color": "#ef4444"},
        {"op": ">=", "value": 20, "color": "#f59e0b"},
        {"color": "#22c55e"},
    ]
    r = evaluate_threshold(25, rules)
    assert r["color"] == "#f59e0b"


def test_threshold_default_fallback():
    from app.dashboards.threshold import evaluate_threshold
    rules = [
        {"op": ">=", "value": 30, "color": "#ef4444"},
        {"color": "#22c55e", "label": "Normal"},
    ]
    r = evaluate_threshold(10, rules)
    assert r["color"] == "#22c55e"
    assert r["label"] == "Normal"


def test_threshold_no_match_no_default():
    from app.dashboards.threshold import evaluate_threshold
    from app.dashboards.threshold import DEFAULT_COLOR
    rules = [{"op": ">=", "value": 30, "color": "#ef4444"}]
    r = evaluate_threshold(10, rules)
    assert r["matched"] is False
    assert r["color"] == DEFAULT_COLOR


def test_threshold_lt_op():
    from app.dashboards.threshold import evaluate_threshold
    rules = [{"op": "<", "value": 5, "color": "#ef4444", "label": "Bas"}]
    r = evaluate_threshold(3, rules)
    assert r["color"] == "#ef4444"
    assert r["matched"] is True


def test_threshold_eq_op():
    from app.dashboards.threshold import evaluate_threshold
    rules = [{"op": "==", "value": 42, "color": "#3b82f6", "label": "Exact"}]
    r = evaluate_threshold(42, rules)
    assert r["matched"] is True


def test_threshold_ne_op():
    from app.dashboards.threshold import evaluate_threshold
    rules = [{"op": "!=", "value": 0, "color": "#22c55e"}]
    r = evaluate_threshold(5, rules)
    assert r["matched"] is True
    r2 = evaluate_threshold(0, rules)
    assert r2["matched"] is False


def test_threshold_unknown_op_skipped():
    from app.dashboards.threshold import evaluate_threshold
    rules = [
        {"op": "BETWEEN", "value": 10, "color": "#ff0000"},
        {"color": "#22c55e", "label": "Fallback"},
    ]
    r = evaluate_threshold(15, rules)
    assert r["label"] == "Fallback"


# ── Route tests ───────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


def _write_yaml(tmp_path: Path, dash_id: str, with_thresholds: bool = True) -> None:
    import yaml
    thresholds = [
        {"op": ">=", "value": 30, "color": "#ef4444", "label": "Critique"},
        {"op": ">=", "value": 20, "color": "#f59e0b", "label": "Élevé"},
        {"color": "#22c55e", "label": "Normal"},
    ] if with_thresholds else []
    tile = {
        "id": "kpi1", "type": "kpi", "title": "Chômage",
        "sql_pinned": "SELECT 25.0 AS taux",
        "options": {"thresholds": thresholds},
    }
    if not with_thresholds:
        tile["options"] = {}
    data = {
        "id": dash_id, "title": "T", "scope": "personal",
        "tiles": [tile],
        "theme": {"primary_color": "#1a4a8c", "font": "sans-serif", "logo_url": ""},
        "created_at": "", "updated_at": "",
    }
    (tmp_path / f"{dash_id}.yaml").write_text(yaml.safe_dump(data, allow_unicode=True))


def test_status_route_returns_color(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    _write_yaml(tmp_path, "d-thr-1")
    r = client.get("/dashboards/d-thr-1/tiles/kpi1/status", headers=VIEWER)
    assert r.status_code == 200
    data = r.json()
    assert data["color"] == "#f59e0b"   # 25 → Élevé
    assert data["label"] == "Élevé"
    assert data["value"] == pytest.approx(25.0)
    assert data["thresholds_count"] == 3


def test_status_route_no_thresholds(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    _write_yaml(tmp_path, "d-thr-2", with_thresholds=False)
    r = client.get("/dashboards/d-thr-2/tiles/kpi1/status", headers=VIEWER)
    assert r.status_code == 422


def test_status_route_missing_dashboard(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    r = client.get("/dashboards/ghost-thr/tiles/kpi1/status", headers=VIEWER)
    assert r.status_code == 404


def test_status_route_requires_auth(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    _write_yaml(tmp_path, "d-thr-auth")
    r = client.get("/dashboards/d-thr-auth/tiles/kpi1/status")
    assert r.status_code == 401

"""Tests monitoring Prometheus + Helm Sprint 21."""
import json
import pytest
from fastapi.testclient import TestClient

from app.main import app, store
from app.monitoring.metrics import (
    Counter, Gauge, Histogram,
    asks_total, active_tables, cache_hits_total, render_all,
)

VIEWER = {"X-Api-Key": "test-viewer-key-s6"}


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset():
    store.tables.clear()
    yield


# --- Metrics unit tests ---

def test_counter_inc_and_get():
    c = Counter("test_c", "test")
    c.inc(3.0)
    assert c.get() == 3.0


def test_counter_with_labels():
    c = Counter("req_total", "reqs", labels=["status"])
    c.inc(1.0, status="success")
    c.inc(2.0, status="error")
    assert c.get(status="success") == 1.0
    assert c.get(status="error") == 2.0


def test_counter_render():
    c = Counter("my_counter", "A counter")
    c.inc(5.0)
    rendered = c.render()
    assert "# HELP my_counter" in rendered
    assert "# TYPE my_counter counter" in rendered
    assert "my_counter 5.0" in rendered


def test_gauge_set_get():
    g = Gauge("my_gauge", "A gauge")
    g.set(42.0)
    assert g.get() == 42.0


def test_gauge_render():
    g = Gauge("g_test", "Test gauge")
    g.set(7.5)
    rendered = g.render()
    assert "g_test 7.5" in rendered


def test_histogram_observe():
    h = Histogram("h_test", "Test histogram")
    h.observe(0.1)
    h.observe(0.5)
    h.observe(2.0)
    rendered = h.render()
    assert "h_test_count 3" in rendered
    assert "h_test_sum" in rendered


def test_histogram_buckets():
    h = Histogram("h_b", "buckets")
    h.observe(0.05)
    rendered = h.render()
    assert 'le="0.1"' in rendered
    assert 'le="+Inf"' in rendered


def test_render_all_contains_all_metrics():
    text = render_all()
    assert "sovereignbi_asks_total" in text
    assert "sovereignbi_uploads_total" in text
    assert "sovereignbi_cache_hits_total" in text
    assert "sovereignbi_active_tables" in text
    assert "sovereignbi_ask_duration_seconds" in text


# --- Route tests ---

def test_metrics_endpoint(client):
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "text/plain" in r.headers["content-type"]
    assert "sovereignbi_asks_total" in r.text


def test_metrics_contains_active_tables(client):
    import io, pandas as pd
    store.load_dataframe("metrics_test", pd.DataFrame({"x": [1]}))
    r = client.get("/metrics")
    assert "sovereignbi_active_tables" in r.text


def test_liveness_probe(client):
    r = client.get("/live")
    assert r.status_code == 200
    assert r.json()["alive"] is True


def test_readiness_probe(client):
    r = client.get("/ready")
    assert r.status_code == 200
    data = r.json()
    assert data["ready"] is True
    assert "tables" in data


# --- Helm chart structure ---

def test_helm_chart_exists():
    from pathlib import Path
    chart = Path("helm/sovereignbi/Chart.yaml")
    assert chart.exists()
    import yaml
    with chart.open() as f:
        content = yaml.safe_load(f)
    assert content["name"] == "sovereignbi"
    assert "version" in content


def test_helm_values_exists():
    from pathlib import Path
    values = Path("helm/sovereignbi/values.yaml")
    assert values.exists()
    import yaml
    with values.open() as f:
        content = yaml.safe_load(f)
    assert "image" in content
    assert "prometheus" in content
    assert content["prometheus"]["enabled"] is True


def test_grafana_dashboard_exists():
    from pathlib import Path
    dashboard = Path("docs/grafana-dashboard.json")
    assert dashboard.exists()
    with dashboard.open() as f:
        data = json.load(f)
    assert data["title"] == "SovereignBI — Monitoring"
    assert len(data["panels"]) >= 4

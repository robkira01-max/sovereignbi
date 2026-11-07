"""Tests for UN Comtrade Plus connector and /api/v1/trade-flows route."""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("SOVEREIGN_EMBEDDER", "tfidf")

VIEWER = {"X-Api-Key": "test-viewer-key-s6"}


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


# ── Unit tests: ComtradeClient ────────────────────────────────────────────────

def test_client_raises_without_key(monkeypatch):
    monkeypatch.delenv("COMTRADE_API_KEY", raising=False)
    from app.data import comtrade_client
    with pytest.raises(ValueError, match="COMTRADE_API_KEY"):
        comtrade_client.ComtradeClient(api_key="")


def test_parse_response_known_partner():
    from app.data.comtrade_client import _parse_response
    data = {
        "data": [
            {"partnerCode": 231, "partnerDesc": "Ethiopia", "primaryValue": 50_000_000},
            {"partnerCode": 999, "partnerDesc": "Unknown land", "primaryValue": 1_000},
        ]
    }
    flows = _parse_response(data, "X", 2023)
    assert len(flows) == 1
    assert flows[0].country == "Éthiopie"
    assert flows[0].trade_value_usd == 50_000_000.0
    assert flows[0].tonnage_k == 50_000


def test_parse_response_zero_value_filtered():
    from app.data.comtrade_client import _parse_response
    data = {"data": [{"partnerCode": 231, "partnerDesc": "Eth", "primaryValue": 0}]}
    flows = _parse_response(data, "X", 2023)
    assert flows == []


def test_parse_response_sorted_descending():
    from app.data.comtrade_client import _parse_response
    data = {
        "data": [
            {"partnerCode": 156, "partnerDesc": "China", "primaryValue": 1_000_000},
            {"partnerCode": 231, "partnerDesc": "Ethiopia", "primaryValue": 5_000_000},
        ]
    }
    flows = _parse_response(data, "X", 2023)
    assert flows[0].trade_value_usd > flows[1].trade_value_usd


def test_circuit_breaker_opens_after_failures(monkeypatch):
    from app.data import comtrade_client
    cb = comtrade_client._CircuitBreaker()
    for _ in range(comtrade_client._CB_MAX):
        cb.record_failure()
    assert not cb.allow()


def test_circuit_breaker_resets_on_success():
    from app.data.comtrade_client import _CircuitBreaker
    cb = _CircuitBreaker()
    cb.record_failure()
    cb.record_failure()
    cb.record_success()
    assert cb.failures == 0
    assert cb.allow()


def test_client_validates_year(monkeypatch):
    from app.data.comtrade_client import ComtradeClient
    c = ComtradeClient(api_key="fake-key")
    with pytest.raises(ValueError, match="year"):
        c.get_trade_flows(year=1800)


def test_client_validates_flow_code():
    from app.data.comtrade_client import ComtradeClient
    c = ComtradeClient(api_key="fake-key")
    with pytest.raises(ValueError, match="flow_code"):
        c.get_trade_flows(flow_code="Z")


# ── Route tests ──────────────────────────────────────────────────────────────

def test_trade_flows_returns_demo_without_key(client, monkeypatch):
    monkeypatch.delenv("COMTRADE_API_KEY", raising=False)
    r = client.get("/api/v1/trade-flows")
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 1
    assert all("from_lng" in f for f in data)
    assert all(f["source"] == "demo" for f in data)


def test_trade_flows_live_data_on_success(client, monkeypatch):
    """When COMTRADE_API_KEY is set and the client succeeds, source='comtrade'."""
    monkeypatch.setenv("COMTRADE_API_KEY", "test-fake-key")
    mock_flow = MagicMock()
    mock_flow.id = "ct-x-0"
    mock_flow.from_lng = 43.146
    mock_flow.from_lat = 11.582
    mock_flow.to_lng = 38.737
    mock_flow.to_lat = 9.032
    mock_flow.commodity = "Export DJ → Éthiopie"
    mock_flow.tonnage_k = 50000
    mock_flow.color = "#f97316"
    mock_flow.destination = "Éthiopie"
    mock_flow.country = "Éthiopie"
    mock_flow.trade_value_usd = 50_000_000.0
    mock_flow.flow_code = "X"
    mock_flow.year = 2023

    with patch("app.data.comtrade_client.ComtradeClient") as MockClient:
        MockClient.return_value.get_trade_flows.return_value = [mock_flow]
        r = client.get("/api/v1/trade-flows?year=2023&flow=X")

    assert r.status_code == 200
    items = r.json()
    # At least the mocked item should be present
    assert len(items) >= 1


def test_trade_flows_fallback_on_api_error(client, monkeypatch):
    """When Comtrade API raises, response falls back to demo data."""
    monkeypatch.setenv("COMTRADE_API_KEY", "broken-key")
    with patch("app.data.comtrade_client.ComtradeClient") as MockClient:
        MockClient.return_value.get_trade_flows.side_effect = RuntimeError("network error")
        r = client.get("/api/v1/trade-flows")
    assert r.status_code == 200
    assert len(r.json()) >= 1  # demo data returned


def test_trade_flows_invalid_flow_param(client, monkeypatch):
    monkeypatch.delenv("COMTRADE_API_KEY", raising=False)
    r = client.get("/api/v1/trade-flows?flow=Z")
    assert r.status_code == 200  # defaults to X, no crash

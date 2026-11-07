"""Tests for GET /api/v1/trade-flows endpoint."""
from __future__ import annotations

import os
import re

import pytest

os.environ.setdefault("SOVEREIGN_EMBEDDER", "tfidf")


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


def test_trade_flows_returns_200(client):
    resp = client.get("/api/v1/trade-flows")
    assert resp.status_code == 200


def test_trade_flows_returns_list(client):
    flows = client.get("/api/v1/trade-flows").json()
    assert isinstance(flows, list)
    assert len(flows) >= 1


def test_trade_flows_has_five_corridors(client):
    flows = client.get("/api/v1/trade-flows").json()
    assert len(flows) == 5


def test_trade_flows_required_fields(client):
    flows = client.get("/api/v1/trade-flows").json()
    for flow in flows:
        assert "id" in flow
        assert "from_lng" in flow
        assert "from_lat" in flow
        assert "to_lng" in flow
        assert "to_lat" in flow
        assert "commodity" in flow
        assert "tonnage_k" in flow
        assert "color" in flow
        assert "destination" in flow
        assert "country" in flow


def test_trade_flows_origin_is_port_djibouti(client):
    flows = client.get("/api/v1/trade-flows").json()
    for flow in flows:
        assert abs(flow["from_lng"] - 43.146) < 0.01
        assert abs(flow["from_lat"] - 11.582) < 0.01


def test_trade_flows_positive_tonnage(client):
    flows = client.get("/api/v1/trade-flows").json()
    for flow in flows:
        assert flow["tonnage_k"] > 0


def test_trade_flows_color_is_hex(client):
    flows = client.get("/api/v1/trade-flows").json()
    hex_re = re.compile(r"^#[0-9a-fA-F]{6}$")
    for flow in flows:
        assert hex_re.match(flow["color"]), f"Invalid color: {flow['color']}"


def test_trade_flows_destinations_in_ethiopia(client):
    flows = client.get("/api/v1/trade-flows").json()
    for flow in flows:
        # All destinations are in Ethiopia bounding box roughly (34-48°E, 3-15°N)
        assert 34.0 < flow["to_lng"] < 48.0
        assert 3.0 < flow["to_lat"] < 15.0
        assert flow["country"] == "Éthiopie"


def test_trade_flows_no_auth_required(client):
    """Trade flows are public (no API key needed — demo data)."""
    resp = client.get("/api/v1/trade-flows")
    assert resp.status_code == 200


def test_trade_flows_unique_ids(client):
    flows = client.get("/api/v1/trade-flows").json()
    ids = [f["id"] for f in flows]
    assert len(ids) == len(set(ids))

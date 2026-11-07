"""Tests for the MCP server router (GET /mcp/info, POST /mcp/rpc)."""
from __future__ import annotations

import os
import json

import pytest

os.environ.setdefault("SOVEREIGN_EMBEDDER", "tfidf")

VIEWER = {"X-Api-Key": "test-viewer-key-s6"}
EDITOR = {"X-Api-Key": "test-editor-key-s6"}
NO_KEY = {}

RPC = "/mcp/rpc"
INFO = "/mcp/info"


def _rpc(method: str, params: dict | None = None, id_: int = 1) -> dict:
    return {"jsonrpc": "2.0", "id": id_, "method": method, "params": params or {}}


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


# ── /mcp/info ────────────────────────────────────────────────────────────────

def test_mcp_info_returns_200(client):
    resp = client.get(INFO)
    assert resp.status_code == 200


def test_mcp_info_has_five_tools(client):
    data = client.get(INFO).json()
    tools = data["result"]["tools"]
    assert len(tools) == 5


def test_mcp_info_tool_names(client):
    data = client.get(INFO).json()
    names = {t["name"] for t in data["result"]["tools"]}
    assert "mizan_list_dashboards" in names
    assert "mizan_get_dashboard" in names
    assert "mizan_get_tile_data" in names
    assert "mizan_list_tables" in names
    assert "mizan_create_dashboard" in names


def test_mcp_info_server_info(client):
    data = client.get(INFO).json()
    assert data["result"]["serverInfo"]["name"] == "mizan-bi"


# ── /mcp/rpc — protocol ──────────────────────────────────────────────────────

def test_mcp_rpc_requires_auth(client):
    resp = client.post(RPC, json=_rpc("initialize"), headers=NO_KEY)
    assert resp.status_code == 401


def test_mcp_initialize(client):
    resp = client.post(RPC, json=_rpc("initialize"), headers=VIEWER)
    assert resp.status_code == 200
    data = resp.json()
    assert data["result"]["serverInfo"]["name"] == "mizan-bi"
    assert "protocolVersion" in data["result"]


def test_mcp_tools_list(client):
    resp = client.post(RPC, json=_rpc("tools/list"), headers=VIEWER)
    assert resp.status_code == 200
    tools = resp.json()["result"]["tools"]
    assert len(tools) == 5


def test_mcp_unknown_method_returns_32601(client):
    resp = client.post(RPC, json=_rpc("not/a/method"), headers=VIEWER)
    data = resp.json()
    assert data["error"]["code"] == -32601


def test_mcp_invalid_jsonrpc_version(client):
    resp = client.post(RPC, json={"jsonrpc": "1.0", "id": 1, "method": "initialize", "params": {}}, headers=VIEWER)
    data = resp.json()
    assert data["error"]["code"] == -32600


# ── tools/call — read tools ──────────────────────────────────────────────────

def test_mcp_list_dashboards(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.mcp._DASHBOARDS_DIR", tmp_path)
    resp = client.post(RPC, json=_rpc("tools/call", {"name": "mizan_list_dashboards", "arguments": {}}), headers=VIEWER)
    assert resp.status_code == 200
    result = resp.json()["result"]
    assert "content" in result
    items = json.loads(result["content"][0]["text"])
    assert isinstance(items, list)


def test_mcp_get_dashboard_not_found(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.mcp._DASHBOARDS_DIR", tmp_path)
    resp = client.post(
        RPC,
        json=_rpc("tools/call", {"name": "mizan_get_dashboard", "arguments": {"dashboard_id": "ghost"}}),
        headers=VIEWER,
    )
    result = resp.json()["result"]
    assert result.get("isError") is True
    assert "introuvable" in result["content"][0]["text"]


def test_mcp_list_tables_empty(client):
    resp = client.post(RPC, json=_rpc("tools/call", {"name": "mizan_list_tables", "arguments": {}}), headers=VIEWER)
    result = resp.json()["result"]
    assert "content" in result
    tables = json.loads(result["content"][0]["text"])
    assert isinstance(tables, list)


def test_mcp_unknown_tool_returns_32601(client):
    resp = client.post(RPC, json=_rpc("tools/call", {"name": "mizan_does_not_exist", "arguments": {}}), headers=VIEWER)
    data = resp.json()
    assert data["error"]["code"] == -32601


# ── tools/call — create_dashboard ────────────────────────────────────────────

def test_mcp_create_dashboard_requires_editor(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.mcp._DASHBOARDS_DIR", tmp_path)
    spec = {"id": "test-mcp-dash", "title": "Test MCP", "tiles": []}
    resp = client.post(
        RPC,
        json=_rpc("tools/call", {"name": "mizan_create_dashboard", "arguments": {"spec": spec}}),
        headers=VIEWER,
    )
    result = resp.json()["result"]
    assert result.get("isError") is True
    assert "editor" in result["content"][0]["text"]


def test_mcp_create_dashboard_success(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.mcp._DASHBOARDS_DIR", tmp_path)
    spec = {
        "id": "mcp-created",
        "title": "Dashboard via MCP",
        "tiles": [{"id": "t1", "type": "kpi", "title": "KPI", "metric": "SELECT 42"}],
    }
    resp = client.post(
        RPC,
        json=_rpc("tools/call", {"name": "mizan_create_dashboard", "arguments": {"spec": spec}}),
        headers=EDITOR,
    )
    result = resp.json()["result"]
    assert result.get("isError") is not True
    payload = json.loads(result["content"][0]["text"])
    assert payload["id"] == "mcp-created"
    assert (tmp_path / "mcp-created.yaml").exists()


def test_mcp_create_dashboard_missing_id(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.mcp._DASHBOARDS_DIR", tmp_path)
    spec = {"title": "No ID"}
    resp = client.post(
        RPC,
        json=_rpc("tools/call", {"name": "mizan_create_dashboard", "arguments": {"spec": spec}}),
        headers=EDITOR,
    )
    result = resp.json()["result"]
    assert result.get("isError") is True
    assert "requis" in result["content"][0]["text"]


def test_mcp_notifications_initialized(client):
    resp = client.post(RPC, json={"jsonrpc": "2.0", "id": None, "method": "notifications/initialized", "params": {}}, headers=VIEWER)
    assert resp.status_code == 200
    data = resp.json()
    assert "result" in data

#!/usr/bin/env python3
"""MizanBI MCP stdio server — Claude Code integration.

Add to .claude.json:
  "mcpServers": {
    "mizan-bi": {
      "command": "python",
      "args": ["tools/mcp_server.py"],
      "cwd": "/path/to/sovereignbi",
      "env": {
        "SOVEREIGN_VIEWER_KEY": "...",
        "SOVEREIGN_EDITOR_KEY": "...",
        "SOVEREIGN_EMBEDDER": "tfidf"
      }
    }
  }
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("SOVEREIGN_EMBEDDER", "tfidf")

from app.routers.mcp import (  # noqa: E402
    TOOLS,
    _SERVER_INFO,
    _CAPABILITIES,
    _tool_create_dashboard,
    _tool_get_dashboard,
    _tool_get_tile_data,
    _tool_list_dashboards,
    _tool_list_tables,
)


def _write(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _get_role() -> str:
    for role in ("admin", "editor", "viewer"):
        if os.environ.get(f"SOVEREIGN_{role.upper()}_KEY", ""):
            return role
    return "viewer"


def run() -> None:
    try:
        from app.data.duckdb_store import DataStore
        store = DataStore()
    except Exception:
        store = None

    role = _get_role()

    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            _write({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}})
            continue

        id_ = msg.get("id")
        method = msg.get("method", "")
        params = msg.get("params") or {}

        if method == "initialize":
            _write({
                "jsonrpc": "2.0", "id": id_,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": _SERVER_INFO,
                    "capabilities": _CAPABILITIES,
                },
            })
        elif method in {"initialized", "notifications/initialized"}:
            pass
        elif method == "tools/list":
            _write({"jsonrpc": "2.0", "id": id_, "result": {"tools": TOOLS}})
        elif method == "tools/call":
            tool_name = params.get("name", "")
            tool_params = params.get("arguments") or {}
            if tool_name == "mizan_list_dashboards":
                result = _tool_list_dashboards()
            elif tool_name == "mizan_get_dashboard":
                result = _tool_get_dashboard(tool_params)
            elif tool_name == "mizan_get_tile_data":
                result = _tool_get_tile_data(tool_params, store)
            elif tool_name == "mizan_list_tables":
                result = _tool_list_tables(store)
            elif tool_name == "mizan_create_dashboard":
                result = _tool_create_dashboard(tool_params, role)
            else:
                _write({"jsonrpc": "2.0", "id": id_, "error": {"code": -32601, "message": f"Outil inconnu : '{tool_name}'"}})
                continue
            _write({"jsonrpc": "2.0", "id": id_, "result": result})
        else:
            _write({"jsonrpc": "2.0", "id": id_, "error": {"code": -32601, "message": f"Méthode inconnue : '{method}'"}})


if __name__ == "__main__":
    run()

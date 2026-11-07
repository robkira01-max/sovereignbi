"""MCP (Model Context Protocol) server — exposes MizanBI dashboards as LLM tools.

Protocol: JSON-RPC 2.0 over HTTP POST /mcp/rpc
Authentication: X-Api-Key header (viewer=read, editor=write)
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, Depends, Request

from app.dashboards.models import Dashboard, DashboardTheme, Tile, load_dashboard, save_dashboard
from app.security.rbac import ROLES, RequireRole

router = APIRouter(prefix="/mcp", tags=["mcp"])

_VIEWER = RequireRole("viewer")
_DASHBOARDS_DIR = Path("data/dashboards")
_ID_RE = re.compile(r'^[A-Za-z0-9_\-]{1,128}$')

_SERVER_INFO: dict = {"name": "mizan-bi", "version": "0.1.0"}
_CAPABILITIES: dict = {"tools": {"listChanged": False}}

TOOLS: list[dict] = [
    {
        "name": "mizan_list_dashboards",
        "description": "List all available MizanBI dashboards. Returns id, title, scope, tile_count, updated_at.",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "mizan_get_dashboard",
        "description": "Get the full definition of a MizanBI dashboard including all tiles.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "dashboard_id": {"type": "string", "description": "Dashboard identifier."},
            },
            "required": ["dashboard_id"],
        },
    },
    {
        "name": "mizan_get_tile_data",
        "description": "Execute a tile's SQL query and return the resulting rows (up to limit rows).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "dashboard_id": {"type": "string"},
                "tile_id": {"type": "string"},
                "limit": {
                    "type": "integer",
                    "description": "Max rows to return (default 50, max 200).",
                    "default": 50,
                },
            },
            "required": ["dashboard_id", "tile_id"],
        },
    },
    {
        "name": "mizan_list_tables",
        "description": "List all tables in the MizanBI DuckDB data store with column names, types, and row counts.",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "mizan_create_dashboard",
        "description": (
            "Create a new MizanBI dashboard (requires editor role). "
            "Spec: {id, title, scope?, tiles: [{id, type, title, sql_pinned?, metric?}]}."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "spec": {"type": "object", "description": "Dashboard specification."},
            },
            "required": ["spec"],
        },
    },
]


# ── Wire helpers ─────────────────────────────────────────────────────────────

def _validate_id(value: str, label: str = "id") -> None:
    if not _ID_RE.match(value):
        raise ValueError(f"{label} invalide : caractères autorisés a-z A-Z 0-9 _ -")


def _rpc_error(id_: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": message}}


def _rpc_ok(id_: Any, result: Any) -> dict:
    return {"jsonrpc": "2.0", "id": id_, "result": result}


def _tool_text(text: str) -> dict:
    return {"content": [{"type": "text", "text": text}]}


def _tool_error(message: str) -> dict:
    return {"content": [{"type": "text", "text": f"Error: {message}"}], "isError": True}


# ── Tool implementations ──────────────────────────────────────────────────────

def _tool_list_dashboards() -> dict:
    _DASHBOARDS_DIR.mkdir(parents=True, exist_ok=True)
    items = []
    for p in sorted(_DASHBOARDS_DIR.glob("*.yaml")):
        try:
            d = load_dashboard(p)
            items.append({
                "id": d.id,
                "title": d.title,
                "scope": d.scope,
                "tile_count": len(d.tiles),
                "updated_at": d.updated_at,
            })
        except Exception:
            continue
    return _tool_text(json.dumps(items, ensure_ascii=False))


def _tool_get_dashboard(params: dict) -> dict:
    dashboard_id = str(params.get("dashboard_id", ""))
    try:
        _validate_id(dashboard_id, "dashboard_id")
    except ValueError as exc:
        return _tool_error(str(exc))
    _DASHBOARDS_DIR.mkdir(parents=True, exist_ok=True)
    path = _DASHBOARDS_DIR / f"{dashboard_id}.yaml"
    if not path.exists():
        return _tool_error(f"Dashboard '{dashboard_id}' introuvable.")
    try:
        d = load_dashboard(path)
        return _tool_text(json.dumps(asdict(d), ensure_ascii=False, default=str))
    except Exception as exc:
        return _tool_error(str(exc))


def _tool_get_tile_data(params: dict, store: Any) -> dict:
    dashboard_id = str(params.get("dashboard_id", ""))
    tile_id = str(params.get("tile_id", ""))
    try:
        limit = min(max(1, int(params.get("limit", 50))), 200)
    except (TypeError, ValueError):
        limit = 50
    try:
        _validate_id(dashboard_id, "dashboard_id")
        _validate_id(tile_id, "tile_id")
    except ValueError as exc:
        return _tool_error(str(exc))

    _DASHBOARDS_DIR.mkdir(parents=True, exist_ok=True)
    path = _DASHBOARDS_DIR / f"{dashboard_id}.yaml"
    if not path.exists():
        return _tool_error(f"Dashboard '{dashboard_id}' introuvable.")
    try:
        d = load_dashboard(path)
    except Exception as exc:
        return _tool_error(f"Erreur lecture dashboard : {exc}")

    tile = next((t for t in d.tiles if t.id == tile_id), None)
    if tile is None:
        return _tool_error(f"Tuile '{tile_id}' introuvable.")

    sql = (tile.sql_pinned or tile.metric or "").strip()
    if not sql:
        return _tool_error(f"La tuile '{tile_id}' n'a pas de SQL exécutable.")
    if store is None:
        return _tool_error("Magasin de données non disponible.")
    try:
        safe = sql.rstrip(";")
        if "LIMIT" not in safe.upper():
            safe = f"SELECT * FROM ({safe}) _q LIMIT {limit}"
        cols, rows = store.execute(safe)
        payload = {"columns": cols, "rows": [list(r) for r in rows], "row_count": len(rows)}
        return _tool_text(json.dumps(payload, ensure_ascii=False, default=str))
    except Exception as exc:
        return _tool_error(f"Erreur SQL : {exc}")


def _tool_list_tables(store: Any) -> dict:
    if store is None:
        return _tool_error("Magasin de données non disponible.")
    try:
        tables = []
        for t in sorted(store.tables):
            cols = store.con.execute(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_name = ? ORDER BY ordinal_position",
                [t],
            ).fetchall()
            cnt = store.con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()
            tables.append({
                "name": t,
                "columns": [{"name": c, "type": dt} for c, dt in cols],
                "row_count": cnt[0] if cnt else 0,
            })
        return _tool_text(json.dumps(tables, ensure_ascii=False))
    except Exception as exc:
        return _tool_error(str(exc))


def _tool_create_dashboard(params: dict, role: str) -> dict:
    if ROLES.get(role, 0) < ROLES["editor"]:
        return _tool_error("Rôle 'editor' requis pour créer un dashboard.")
    spec = params.get("spec")
    if not isinstance(spec, dict):
        return _tool_error("Le paramètre 'spec' doit être un objet JSON.")
    dashboard_id = str(spec.get("id", ""))
    if not dashboard_id:
        return _tool_error("Le champ 'id' est requis dans spec.")
    try:
        _validate_id(dashboard_id, "id")
    except ValueError as exc:
        return _tool_error(str(exc))
    try:
        now = datetime.now(timezone.utc).isoformat()
        theme_data = spec.get("theme", {})
        d = Dashboard(
            id=dashboard_id,
            title=spec.get("title", dashboard_id),
            scope=spec.get("scope", "personal"),
            tiles=[
                Tile(
                    id=t["id"],
                    type=t["type"],
                    title=t.get("title", t["id"]),
                    metric=t.get("metric"),
                    sql_pinned=t.get("sql_pinned"),
                    dimensions=t.get("dimensions", []),
                    filters=t.get("filters", {}),
                    options=t.get("options", {}),
                )
                for t in spec.get("tiles", [])
            ],
            theme=DashboardTheme(
                primary_color=theme_data.get("primary_color", "#1f77b4"),
                font=theme_data.get("font", "sans-serif"),
                logo_url=theme_data.get("logo_url", ""),
            ),
            created_at=now,
            updated_at=now,
        )
        _DASHBOARDS_DIR.mkdir(parents=True, exist_ok=True)
        save_dashboard(d, _DASHBOARDS_DIR / f"{dashboard_id}.yaml")
        return _tool_text(json.dumps({"id": d.id, "updated_at": d.updated_at}, ensure_ascii=False))
    except Exception as exc:
        return _tool_error(str(exc))


# ── HTTP endpoints ─────────────────────────────────────────────────────────────

@router.get("/info")
def mcp_info():
    """Public endpoint: MCP server capabilities and tool list (no auth required)."""
    return {
        "jsonrpc": "2.0",
        "result": {
            "serverInfo": _SERVER_INFO,
            "capabilities": _CAPABILITIES,
            "tools": TOOLS,
        },
    }


@router.post("/rpc")
async def mcp_rpc(
    request: Request,
    body: dict = Body(...),
    role: str = Depends(_VIEWER),
) -> dict:
    """JSON-RPC 2.0 endpoint — handles all MCP messages."""
    id_ = body.get("id")
    method = body.get("method", "")
    params = body.get("params") or {}

    if body.get("jsonrpc") != "2.0":
        return _rpc_error(id_, -32600, "jsonrpc 2.0 requis.")

    store = getattr(request.app.state, "store", None)

    if method == "initialize":
        return _rpc_ok(id_, {
            "protocolVersion": "2024-11-05",
            "serverInfo": _SERVER_INFO,
            "capabilities": _CAPABILITIES,
        })

    if method in {"notifications/initialized", "initialized"}:
        return _rpc_ok(id_, {})

    if method == "tools/list":
        return _rpc_ok(id_, {"tools": TOOLS})

    if method == "tools/call":
        tool_name = params.get("name", "")
        tool_params = params.get("arguments") or {}
        dispatch: dict[str, Any] = {
            "mizan_list_dashboards":  lambda: _tool_list_dashboards(),
            "mizan_get_dashboard":    lambda: _tool_get_dashboard(tool_params),
            "mizan_get_tile_data":    lambda: _tool_get_tile_data(tool_params, store),
            "mizan_list_tables":      lambda: _tool_list_tables(store),
            "mizan_create_dashboard": lambda: _tool_create_dashboard(tool_params, role),
        }
        fn = dispatch.get(tool_name)
        if fn is None:
            return _rpc_error(id_, -32601, f"Outil inconnu : '{tool_name}'")
        return _rpc_ok(id_, fn())

    return _rpc_error(id_, -32601, f"Méthode inconnue : '{method}'")

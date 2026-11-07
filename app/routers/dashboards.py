"""Dashboard and template API routes."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse

from app.dashboards.models import (
    Dashboard,
    DashboardTemplate,
    load_dashboard,
    load_template,
    save_dashboard,
)
from app.security.rbac import RequireRole

router = APIRouter(tags=["dashboards"])

_VIEWER = RequireRole("viewer")
_EDITOR = RequireRole("editor")

_DASHBOARDS_DIR = Path("data/dashboards")
_TEMPLATES_DIR = Path("templates")

_ID_RE = re.compile(r'^[A-Za-z0-9_\-]{1,128}$')


def _validate_id(value: str, label: str = "id") -> None:
    """Reject path-traversal and shell-injection attempts in IDs."""
    if not _ID_RE.match(value):
        raise HTTPException(400, f"{label} invalide : caractères autorisés a-z A-Z 0-9 _ -")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Dashboards ───────────────────────────────────────────────────────────────

@router.get("/dashboards")
def list_dashboards(
    _: str = Depends(_VIEWER),
    skip: int = Query(0, ge=0, description="Nombre d'éléments à sauter"),
    limit: int = Query(50, ge=1, le=200, description="Nombre d'éléments à retourner"),
):
    # 13 — Pagination pour éviter de charger des centaines de dashboards d'un coup.
    _DASHBOARDS_DIR.mkdir(parents=True, exist_ok=True)
    items = []
    for p in sorted(_DASHBOARDS_DIR.glob("*.yaml")):
        try:
            d = load_dashboard(p)
            items.append({"id": d.id, "title": d.title, "scope": d.scope, "updated_at": d.updated_at})
        except Exception:
            continue
    total = len(items)
    return {"dashboards": items[skip: skip + limit], "total": total, "skip": skip, "limit": limit}


@router.get("/dashboards/{dashboard_id}")
def get_dashboard(dashboard_id: str, _: str = Depends(_VIEWER)):
    _validate_id(dashboard_id, "dashboard_id")
    _DASHBOARDS_DIR.mkdir(parents=True, exist_ok=True)
    p = _DASHBOARDS_DIR / f"{dashboard_id}.yaml"
    if not p.exists():
        raise HTTPException(404, f"Dashboard '{dashboard_id}' introuvable.")
    try:
        d = load_dashboard(p)
    except Exception as e:
        raise HTTPException(500, str(e)) from e
    from dataclasses import asdict
    return asdict(d)


@router.post("/dashboards")
def create_dashboard(body: dict = Body(...), _: str = Depends(_EDITOR)):
    _DASHBOARDS_DIR.mkdir(parents=True, exist_ok=True)
    dashboard_id = body.get("id")
    if not dashboard_id:
        raise HTTPException(400, "Le champ 'id' est requis.")
    _validate_id(dashboard_id, "dashboard_id")
    from app.dashboards.models import DashboardTheme, Tile

    tiles = [
        Tile(
            id=t["id"],
            type=t["type"],
            title=t["title"],
            metric=t.get("metric"),
            sql_pinned=t.get("sql_pinned"),
            dimensions=t.get("dimensions", []),
            filters=t.get("filters", {}),
            options=t.get("options", {}),
        )
        for t in body.get("tiles", [])
    ]
    theme_data = body.get("theme", {})
    theme = DashboardTheme(
        primary_color=theme_data.get("primary_color", "#1f77b4"),
        font=theme_data.get("font", "sans-serif"),
        logo_url=theme_data.get("logo_url", ""),
    )
    now = _now()
    d = Dashboard(
        id=dashboard_id,
        title=body.get("title", dashboard_id),
        scope=body.get("scope", "personal"),
        tiles=tiles,
        theme=theme,
        created_at=body.get("created_at", now),
        updated_at=now,
    )
    save_dashboard(d, _DASHBOARDS_DIR / f"{dashboard_id}.yaml")
    return {"id": d.id, "updated_at": d.updated_at}


@router.post("/dashboards/{dashboard_id}/pin")
def pin_tile(dashboard_id: str, body: dict = Body(...), _: str = Depends(_EDITOR)):
    """Épingle le SQL d'une réponse chat à une tuile du dashboard."""
    _validate_id(dashboard_id, "dashboard_id")
    _DASHBOARDS_DIR.mkdir(parents=True, exist_ok=True)
    p = _DASHBOARDS_DIR / f"{dashboard_id}.yaml"
    if not p.exists():
        raise HTTPException(404, f"Dashboard '{dashboard_id}' introuvable.")

    tile_id = body.get("tile_id")
    sql = body.get("sql", "")
    title = body.get("title", "")
    if not tile_id or not sql:
        raise HTTPException(400, "Les champs 'tile_id' et 'sql' sont requis.")

    d = load_dashboard(p)
    updated = False
    for tile in d.tiles:
        if tile.id == tile_id:
            tile.sql_pinned = sql
            if title:
                tile.title = title
            updated = True
            break

    if not updated:
        raise HTTPException(404, f"Tuile '{tile_id}' introuvable dans le dashboard.")

    d.updated_at = _now()
    save_dashboard(d, p)
    return {"id": dashboard_id, "tile_id": tile_id, "updated_at": d.updated_at}


@router.patch("/dashboards/{dashboard_id}/layout")
def patch_layout(dashboard_id: str, body: dict = Body(...), _: str = Depends(_EDITOR)):
    """Réordonne les tuiles du dashboard (drag-and-drop).

    Body: {"tiles": [{"id": "t1", "position": 0}, {"id": "t2", "position": 1}, ...]}
    Toutes les tuiles existantes doivent être présentes — pas d'ajout ni de suppression.
    """
    _validate_id(dashboard_id, "dashboard_id")
    p = _DASHBOARDS_DIR / f"{dashboard_id}.yaml"
    if not p.exists():
        raise HTTPException(404, f"Dashboard '{dashboard_id}' introuvable.")

    order_items = body.get("tiles")
    if not isinstance(order_items, list):
        raise HTTPException(400, "Le champ 'tiles' (liste) est requis.")

    d = load_dashboard(p)
    existing_ids = {tile.id for tile in d.tiles}
    incoming_ids = {item.get("id") for item in order_items if isinstance(item, dict)}

    if incoming_ids != existing_ids:
        raise HTTPException(400, "La liste doit contenir exactement les tuiles existantes.")

    position_map = {
        item["id"]: item.get("position", i)
        for i, item in enumerate(order_items)
        if isinstance(item, dict) and "id" in item
    }
    for tile in d.tiles:
        tile.position = position_map.get(tile.id)
    d.tiles.sort(key=lambda t: (t.position is None, t.position or 0))

    d.updated_at = _now()
    save_dashboard(d, p)
    return {"id": dashboard_id, "updated_at": d.updated_at,
            "order": [t.id for t in d.tiles]}


@router.post("/dashboards/{dashboard_id}/tiles")
def add_tile(dashboard_id: str, body: dict = Body(...), _: str = Depends(_EDITOR)):
    """Ajoute une tuile à un dashboard existant."""
    _validate_id(dashboard_id, "dashboard_id")
    p = _DASHBOARDS_DIR / f"{dashboard_id}.yaml"
    if not p.exists():
        raise HTTPException(404, f"Dashboard '{dashboard_id}' introuvable.")

    tile_id = body.get("id")
    tile_type = body.get("type")
    tile_title = body.get("title")
    if not tile_id or not tile_type or not tile_title:
        raise HTTPException(400, "Les champs 'id', 'type' et 'title' sont requis.")

    d = load_dashboard(p)
    if any(t.id == tile_id for t in d.tiles):
        raise HTTPException(409, f"Une tuile avec l'id '{tile_id}' existe déjà.")

    from app.dashboards.models import Tile
    new_tile = Tile(
        id=tile_id,
        type=tile_type,
        title=tile_title,
        metric=body.get("metric"),
        sql_pinned=body.get("sql_pinned"),
        dimensions=body.get("dimensions", []),
        filters=body.get("filters", {}),
        options=body.get("options", {}),
        position=body.get("position", len(d.tiles)),
    )
    d.tiles.append(new_tile)
    d.updated_at = _now()
    save_dashboard(d, p)
    return {"id": dashboard_id, "tile_id": tile_id, "updated_at": d.updated_at}


@router.get("/dashboards/{dashboard_id}/tiles/{tile_id}/data")
def tile_data(dashboard_id: str, tile_id: str, request: Request, _: str = Depends(_VIEWER)):
    """Execute the pinned SQL of a tile and return {columns, rows, error}."""
    _validate_id(dashboard_id, "dashboard_id")
    _validate_id(tile_id, "tile_id")
    p = _DASHBOARDS_DIR / f"{dashboard_id}.yaml"
    if not p.exists():
        raise HTTPException(404, f"Dashboard '{dashboard_id}' introuvable.")
    d = load_dashboard(p)
    tile = next((t for t in d.tiles if t.id == tile_id), None)
    if tile is None:
        raise HTTPException(404, f"Tuile '{tile_id}' introuvable.")
    store = request.app.state.store
    from app.dashboards.renderer import render_tile
    return render_tile(tile, store)


@router.get("/dashboards/{dashboard_id}/tiles/{tile_id}/insight")
def tile_insight(dashboard_id: str, tile_id: str, request: Request, _: str = Depends(_VIEWER)):
    """Generate a one-sentence AI insight for a tile's data (cached 15 min)."""
    _validate_id(dashboard_id, "dashboard_id")
    _validate_id(tile_id, "tile_id")
    p = _DASHBOARDS_DIR / f"{dashboard_id}.yaml"
    if not p.exists():
        raise HTTPException(404, f"Dashboard '{dashboard_id}' introuvable.")
    d = load_dashboard(p)
    tile = next((t for t in d.tiles if t.id == tile_id), None)
    if tile is None:
        raise HTTPException(404, f"Tuile '{tile_id}' introuvable.")
    if not tile.sql_pinned:
        raise HTTPException(422, "Cette tuile n'a pas de SQL épinglé.")

    from app.dashboards.insight import generate_insight, get_cached, set_cached
    cached = get_cached(tile_id, tile.sql_pinned)
    if cached:
        return {"insight": cached, "tile_id": tile_id, "cached": True}

    store = request.app.state.store
    from app.dashboards.renderer import render_tile
    result = render_tile(tile, store)
    if result.get("error") or not result.get("rows"):
        raise HTTPException(422, result.get("error") or "Pas de données pour générer un insight.")

    try:
        from app.llm import get_llm_client
        llm = get_llm_client()
        text = generate_insight(tile.title, result["columns"], result["rows"], llm)
    except Exception as exc:
        raise HTTPException(503, f"LLM indisponible : {exc}") from exc

    set_cached(tile_id, tile.sql_pinned, text)
    return {"insight": text, "tile_id": tile_id, "cached": False}


@router.get("/dashboards/{dashboard_id}/tiles/{tile_id}/delta")
def tile_delta(
    dashboard_id: str,
    tile_id: str,
    request: Request,
    period: str = "mom",
    _: str = Depends(_VIEWER),
):
    """Return sparkline_points + period-over-period delta for a KPI tile.

    period: mom (month-over-month, 12 pts) | yoy (year-over-year, 5 pts) |
            wow (week-over-week, 10 pts).
    """
    _validate_id(dashboard_id, "dashboard_id")
    _validate_id(tile_id, "tile_id")
    p = _DASHBOARDS_DIR / f"{dashboard_id}.yaml"
    if not p.exists():
        raise HTTPException(404, f"Dashboard '{dashboard_id}' introuvable.")
    d = load_dashboard(p)
    tile = next((t for t in d.tiles if t.id == tile_id), None)
    if tile is None:
        raise HTTPException(404, f"Tuile '{tile_id}' introuvable.")
    sql = (tile.sql_pinned or tile.metric or "").strip()
    if not sql:
        raise HTTPException(422, "Cette tuile n'a pas de SQL exécutable.")

    from app.dashboards.delta import compute_delta
    store = request.app.state.store
    result = compute_delta(sql, store, period=period)
    if "error" in result:
        raise HTTPException(422, result["error"])
    return result


@router.get("/dashboards/{dashboard_id}/export/bulletin", response_class=HTMLResponse)
def export_bulletin(dashboard_id: str, request: Request, _: str = Depends(_VIEWER)):
    """Generate a self-contained HTML narrative bulletin for the dashboard."""
    _validate_id(dashboard_id, "dashboard_id")
    p = _DASHBOARDS_DIR / f"{dashboard_id}.yaml"
    if not p.exists():
        raise HTTPException(404, f"Dashboard '{dashboard_id}' introuvable.")
    try:
        d = load_dashboard(p)
    except Exception as e:
        raise HTTPException(500, str(e)) from e

    from app.dashboards.insight import get_cached
    cached_insights: dict[str, str] = {}
    for tile in d.tiles:
        if tile.sql_pinned:
            text = get_cached(tile.id, tile.sql_pinned)
            if text:
                cached_insights[tile.id] = text

    store = request.app.state.store
    from app.dashboards.bulletin import generate_bulletin_html
    html_content = generate_bulletin_html(d, store, cached_insights)
    return HTMLResponse(content=html_content, media_type="text/html; charset=utf-8")


@router.delete("/dashboards/{dashboard_id}/tiles/{tile_id}", status_code=200)
def remove_tile(dashboard_id: str, tile_id: str, _: str = Depends(_EDITOR)):
    """Supprime une tuile d'un dashboard."""
    _validate_id(dashboard_id, "dashboard_id")
    _validate_id(tile_id, "tile_id")
    p = _DASHBOARDS_DIR / f"{dashboard_id}.yaml"
    if not p.exists():
        raise HTTPException(404, f"Dashboard '{dashboard_id}' introuvable.")

    d = load_dashboard(p)
    original_count = len(d.tiles)
    d.tiles = [t for t in d.tiles if t.id != tile_id]
    if len(d.tiles) == original_count:
        raise HTTPException(404, f"Tuile '{tile_id}' introuvable dans le dashboard.")

    d.updated_at = _now()
    save_dashboard(d, p)
    return {"id": dashboard_id, "tile_id": tile_id, "updated_at": d.updated_at}


# ─── Templates ────────────────────────────────────────────────────────────────

@router.get("/templates")
def list_templates(_: str = Depends(_VIEWER)):
    if not _TEMPLATES_DIR.exists():
        return {"templates": []}
    items = []
    for p in sorted(_TEMPLATES_DIR.glob("*.yaml")):
        try:
            t = load_template(p)
            items.append({"id": t.id, "title": t.title, "description": t.description})
        except Exception:
            continue
    return {"templates": items}


@router.get("/templates/{template_id}")
def get_template(template_id: str, _: str = Depends(_VIEWER)):
    if not _TEMPLATES_DIR.exists():
        raise HTTPException(404, "Dossier de templates introuvable.")
    p = _TEMPLATES_DIR / f"{template_id}.yaml"
    if not p.exists():
        # Try matching by id field
        for candidate in _TEMPLATES_DIR.glob("*.yaml"):
            try:
                t = load_template(candidate)
                if t.id == template_id:
                    from dataclasses import asdict
                    return asdict(t)
            except Exception:
                continue
        raise HTTPException(404, f"Template '{template_id}' introuvable.")
    from dataclasses import asdict
    return asdict(load_template(p))

"""Dashboard and template API routes."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Body, Depends, HTTPException

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


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Dashboards ───────────────────────────────────────────────────────────────

@router.get("/dashboards")
def list_dashboards(_: str = Depends(_VIEWER)):
    _DASHBOARDS_DIR.mkdir(parents=True, exist_ok=True)
    items = []
    for p in sorted(_DASHBOARDS_DIR.glob("*.yaml")):
        try:
            d = load_dashboard(p)
            items.append({"id": d.id, "title": d.title, "scope": d.scope, "updated_at": d.updated_at})
        except Exception:
            continue
    return {"dashboards": items}


@router.get("/dashboards/{dashboard_id}")
def get_dashboard(dashboard_id: str, _: str = Depends(_VIEWER)):
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

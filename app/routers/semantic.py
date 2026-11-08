"""Semantic sector switcher — GET/POST /semantic/sectors."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from app.security.rbac import RequireRole
from app.semantic.sectors import list_sectors, load_sector, sector_exists
from app.semantic.model import model_to_prompt_text

router = APIRouter(prefix="/semantic", tags=["semantic"])

_VIEWER = RequireRole("viewer")
_EDITOR = RequireRole("editor")


@router.get("/sectors")
def get_sectors(_: str = Depends(_VIEWER)):
    """List all available sector YAML files."""
    return {"sectors": [{k: v for k, v in s.items() if k != "path"} for s in list_sectors()]}


@router.get("/sectors/active")
def get_active_sector(request: Request, _: str = Depends(_VIEWER)):
    """Return the currently active sector (or 'default')."""
    active = getattr(request.app.state, "active_sector_id", None)
    return {"sector_id": active or "default"}


@router.post("/sectors/{sector_id}/activate")
def activate_sector(sector_id: str, request: Request, _: str = Depends(_EDITOR)):
    """Switch to a sector-specific semantic model, invalidating the LangGraph pipeline.

    The active sector is process-wide (app.state): it changes for every user, hence editor-only.
    """
    if not sector_exists(sector_id):
        raise HTTPException(404, "Secteur introuvable.")
    model = load_sector(sector_id)
    request.app.state.active_sector_id = sector_id
    request.app.state.active_semantic_text = model_to_prompt_text(model)
    # Invalidate the LangGraph pipeline so it rebuilds with the new model
    if hasattr(request.app.state, "get_graph"):
        # Force reset of cached graph by patching the module-level _graph
        import app.main as _main
        _main._graph = None
    return {
        "activated": sector_id,
        "tables": [t.name for t in model.tables],
        "metrics": [m.name for m in model.metrics],
    }


@router.delete("/sectors/active")
def deactivate_sector(request: Request, _: str = Depends(_EDITOR)):
    """Revert to the default semantic model (model.yaml)."""
    request.app.state.active_sector_id = None
    request.app.state.active_semantic_text = None
    import app.main as _main
    _main._graph = None
    return {"activated": "default"}

"""Semantic sector switcher — GET/POST /semantic/sectors."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.security.rbac import RequireRole
from app.semantic.sectors import list_sectors, load_sector, sector_exists
from app.semantic.model import SemanticModel, load_model, model_to_prompt_text
from app.semantic.resolver import resolve_terms
from app.semantic.validate import validate_model

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


def _active_model(request: Request) -> SemanticModel:
    sector_id = getattr(request.app.state, "active_sector_id", None)
    return load_sector(sector_id) if sector_id else load_model()


@router.get("/validate")
def validate_active_model(request: Request, _: str = Depends(_VIEWER)):
    """Contrôle du modèle sémantique actif : doublons, alias ambigus, SQL invalide, colonnes inconnues."""
    model = _active_model(request)
    issues = validate_model(model)
    return {
        "sector_id": getattr(request.app.state, "active_sector_id", None) or "default",
        "ok": not any(i.level == "error" for i in issues),
        "errors": sum(i.level == "error" for i in issues),
        "warnings": sum(i.level == "warning" for i in issues),
        "issues": [i.as_dict() for i in issues],
    }


@router.get("/resolve")
def resolve_question(request: Request, q: str = Query(..., min_length=1, max_length=500), _: str = Depends(_VIEWER)):
    """Aperçu : quels termes métier du modèle actif sont reconnus dans une question (sans appeler le LLM)."""
    model = _active_model(request)
    return {"question": q, "terms": [t.__dict__ for t in resolve_terms(model, q)]}


def _indicator_dict(m) -> dict:
    from app.semantic.validate import SDMX_FREQUENCIES
    meta = {
        "code": m.code, "name": m.name, "aliases": m.aliases, "unit": m.unit, "source": m.source,
        "frequency": m.frequency, "frequency_label": SDMX_FREQUENCIES.get(m.frequency, ""),
        "definition": m.definition or m.description, "methodology": m.methodology,
        "topic": m.topic, "last_updated": m.last_updated,
    }
    missing = [k for k in ("source", "frequency", "unit", "methodology", "last_updated") if not meta[k]]
    return {**meta, "complete": not missing, "missing": missing}


@router.get("/indicators")
def list_indicators(request: Request, topic: str | None = Query(None, max_length=80), _: str = Depends(_VIEWER)):
    """Catalogue des indicateurs publiables du modèle actif (mesures qui portent un `code`) avec leurs métadonnées."""
    items = [_indicator_dict(m) for m in _active_model(request).metrics if m.code]
    if topic:
        items = [i for i in items if i["topic"].lower() == topic.lower()]
    return {"count": len(items), "indicators": items}


@router.get("/indicators/{code}")
def get_indicator(code: str, request: Request, _: str = Depends(_VIEWER)):
    for m in _active_model(request).metrics:
        if m.code and m.code == code:
            return _indicator_dict(m)
    raise HTTPException(404, "Indicateur introuvable.")

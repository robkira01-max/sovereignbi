"""Routes wizard de création guidée et catalogue de templates."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.security.rbac import RequireRole
from app.templates.catalogue import (
    clone_template,
    list_entries,
    list_tags,
    rate_template,
    register_template,
    search_templates,
)
from app.templates.wizard import (
    list_available_dimensions,
    list_available_metrics,
    new_session,
    get_session,
    step_confirm,
    step_generate_preview,
    step_select_dimensions,
    step_select_metrics,
)

router = APIRouter(tags=["wizard", "catalogue"])

_VIEWER = RequireRole("viewer")
_EDITOR = RequireRole("editor")


# ── Wizard ────────────────────────────────────────────────────────────────────

@router.post("/wizard/sessions")
def create_session(_: str = Depends(_EDITOR)):
    session = new_session()
    return {
        "session_id": session.session_id,
        "step": session.step,
        "available_metrics": list_available_metrics(),
        "available_dimensions": list_available_dimensions(),
    }


@router.get("/wizard/sessions/{session_id}")
def read_session(session_id: str, _: str = Depends(_VIEWER)):
    session = get_session(session_id)
    if session is None:
        raise HTTPException(404, f"Session introuvable : {session_id!r}")
    return session


class MetricsRequest(BaseModel):
    metrics: list[str]


@router.post("/wizard/sessions/{session_id}/metrics")
def wizard_metrics(session_id: str, req: MetricsRequest, _: str = Depends(_EDITOR)):
    try:
        return step_select_metrics(session_id, req.metrics)
    except ValueError as e:
        raise HTTPException(400, str(e))


class DimensionsRequest(BaseModel):
    dimensions: list[str]


@router.post("/wizard/sessions/{session_id}/dimensions")
def wizard_dimensions(session_id: str, req: DimensionsRequest, _: str = Depends(_EDITOR)):
    try:
        return step_select_dimensions(session_id, req.dimensions)
    except ValueError as e:
        raise HTTPException(400, str(e))


class PreviewRequest(BaseModel):
    template_name: str


@router.post("/wizard/sessions/{session_id}/preview")
def wizard_preview(session_id: str, req: PreviewRequest, _: str = Depends(_EDITOR)):
    try:
        return step_generate_preview(session_id, req.template_name)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/wizard/sessions/{session_id}/confirm")
def wizard_confirm(session_id: str, _: str = Depends(_EDITOR)):
    try:
        result = step_confirm(session_id)
        register_template(
            result["template_id"],
            title=get_session(session_id).template_name if get_session(session_id) else "Template",
            description="Créé via le wizard",
        )
        return result
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(400, str(e))


# ── Catalogue ─────────────────────────────────────────────────────────────────

@router.get("/catalogue")
def catalogue_list(_: str = Depends(_VIEWER)):
    return list_entries()


@router.get("/catalogue/tags")
def catalogue_tags(_: str = Depends(_VIEWER)):
    return list_tags()


@router.get("/catalogue/search")
def catalogue_search(q: str = "", tags: str = "", _: str = Depends(_VIEWER)):
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    return search_templates(query=q, tags=tag_list)


class RateRequest(BaseModel):
    rating: float


@router.post("/catalogue/{template_id}/rate")
def catalogue_rate(template_id: str, req: RateRequest, _: str = Depends(_EDITOR)):
    try:
        return rate_template(template_id, req.rating)
    except ValueError as e:
        raise HTTPException(400, str(e))


class CloneRequest(BaseModel):
    new_title: str


@router.post("/catalogue/{template_id}/clone")
def catalogue_clone(template_id: str, req: CloneRequest, _: str = Depends(_EDITOR)):
    try:
        return clone_template(template_id, req.new_title)
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(404, str(e))

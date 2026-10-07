"""Routes Marketplace — découverte, templates vedettes, import/export."""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.security.rbac import RequireRole
from app.templates.catalogue import (
    CATALOGUE_PATH,
    get_entry,
    list_tags,
    rate_template,
    search_templates,
)
from app.templates.marketplace import (
    export_template_package,
    get_featured,
    get_trending,
    import_template_package,
    seed_featured_templates,
)

router = APIRouter(prefix="/marketplace", tags=["marketplace"])

_VIEWER = RequireRole("viewer")
_EDITOR = RequireRole("editor")
_ADMIN = RequireRole("admin")


class RateRequest(BaseModel):
    rating: float


class ImportRequest(BaseModel):
    package: dict


@router.get("/featured")
def featured(_: str = Depends(_VIEWER)):
    seed_featured_templates()
    return [asdict(e) for e in get_featured()]


@router.get("/trending")
def trending(limit: int = Query(default=5, ge=1, le=20), _: str = Depends(_VIEWER)):
    return [asdict(e) for e in get_trending(limit=limit)]


@router.get("/search")
def search(
    q: str = Query(default=""),
    tags: str = Query(default=""),
    _: str = Depends(_VIEWER),
):
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    return [asdict(e) for e in search_templates(query=q, tags=tag_list)]


@router.get("/tags")
def tags(_: str = Depends(_VIEWER)):
    seed_featured_templates()
    return {"tags": list_tags()}


@router.post("/templates/{template_id}/rate")
def rate(template_id: str, body: RateRequest, _: str = Depends(_VIEWER)):
    try:
        entry = rate_template(template_id, body.rating)
        return asdict(entry)
    except ValueError as e:
        raise HTTPException(422, str(e))


@router.get("/templates/{template_id}/export")
def export_tmpl(template_id: str, _: str = Depends(_VIEWER)):
    try:
        return export_template_package(template_id)
    except KeyError:
        raise HTTPException(404, "Template introuvable")


@router.post("/templates/import")
def import_tmpl(body: ImportRequest, _: str = Depends(_EDITOR)):
    try:
        entry = import_template_package(body.package)
        return asdict(entry)
    except (ValueError, KeyError) as e:
        raise HTTPException(422, str(e))


@router.post("/seed")
def seed(_: str = Depends(_ADMIN)):
    ids = seed_featured_templates()
    return {"seeded": ids}

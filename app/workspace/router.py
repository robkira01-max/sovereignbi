"""Routes /workspace (P-086a). Lecture = viewer, import = editor, sources et activation = administrateur.

Un utilisateur sans droit sur un dossier reçoit 404 (jamais 403) : ni son existence ni ses fichiers ne se devinent."""
from __future__ import annotations

import re
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.security.actor import actor_label
from app.security.rbac import RequireRole
from app.workspace import paths, service

router = APIRouter(prefix="/workspace", tags=["workspace"])
_VIEWER, _EDITOR, _ADMIN = RequireRole("viewer"), RequireRole("editor"), RequireRole("admin")
_ADMIN_SESSION = RequireRole("admin", session_only=True)      # ce que le serveur expose se décide en session nominative


def _pct(name: str) -> str:
    """Encodage pour `filename*=UTF-8''…` (RFC 5987) : tout octet hors [A-Za-z0-9._-] est encodé."""
    return "".join(chr(b) if chr(b) in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._-" else f"%{b:02X}" for b in name.encode("utf-8"))


def _store(request: Request):
    store = request.app.state.store
    service.ensure_tables(store)
    return store


def _fail(e: service.WorkspaceError):
    raise HTTPException(e.status, str(e)) from None


def _visible_source(store, source_id: int, role: str) -> dict:
    src = service.get_source(store, source_id)
    if not service.visible(src, role):
        raise HTTPException(404, "Ressource introuvable.")
    return src


class SourceCreate(BaseModel):
    type: str = Field(max_length=40)
    name: str = Field(min_length=1, max_length=80)
    root: str = Field(max_length=1024)
    min_role: Literal["viewer", "editor", "admin"] = "viewer"


class SourceState(BaseModel):
    state: Literal["active", "disabled"]


class ImportBody(BaseModel):
    path: str = Field(min_length=1, max_length=1024)


@router.get("/status")
def status(role: str = Depends(_VIEWER)):
    """État de la fonctionnalité, sans chemin du serveur."""
    return {"types_available": [service.TYPE_MOUNTED], "third_party_enabled": service.third_party_allowed(),
            "roots_configured": bool(paths.allowed_roots())}


@router.get("/sources")
def list_sources(request: Request, role: str = Depends(_VIEWER)):
    return service.list_sources(_store(request), role)


@router.post("/sources", status_code=201)
def create_source(body: SourceCreate, request: Request, role: str = Depends(_ADMIN_SESSION)):
    try:
        src = service.create_source(_store(request), type_=body.type, name=body.name, root=body.root, min_role=body.min_role,
                                    actor=actor_label(request, role))
    except service.WorkspaceError as e:
        _fail(e)
    return service.public_source(src, role)


@router.patch("/sources/{source_id}")
def set_state(source_id: int, body: SourceState, request: Request, role: str = Depends(_ADMIN_SESSION)):
    try:
        return service.public_source(service.set_state(_store(request), source_id, body.state, actor_label(request, role)), role)
    except service.WorkspaceError as e:
        _fail(e)


@router.get("/sources/{source_id}/files")
def list_files(source_id: int, request: Request, all_versions: bool = False, role: str = Depends(_VIEWER)):
    store = _store(request)
    src = _visible_source(store, source_id, role)
    out = {"files": service.list_files(store, source_id, role, all_versions=all_versions)}
    if role in ("editor", "admin"):
        out["available"] = service.available_on_disk(store, src)       # parcours du disque : éditeurs seulement
    return out


@router.post("/sources/{source_id}/import")
def import_file(source_id: int, body: ImportBody, request: Request, response: Response, role: str = Depends(_EDITOR)):
    store = _store(request)
    src = _visible_source(store, source_id, role)
    try:
        res = service.import_file(store, src, body.path, actor_label(request, role), role)
    except service.WorkspaceError as e:
        _fail(e)
    response.status_code = 200 if res["unchanged"] else 201
    return res


@router.get("/files/{file_id}/content")
def file_content(file_id: str, request: Request, role: str = Depends(_VIEWER)):
    store = _store(request)
    f = service.get_file(store, file_id)
    src = service.get_source(store, f["source_id"]) if f else None
    if f is None or not service.visible(src, role):
        raise HTTPException(404, "Ressource introuvable.")
    try:
        data, name = service.read_file_content(store, f, actor_label(request, role))
    except service.WorkspaceError as e:
        _fail(e)
    ascii_name = re.sub(r'[^A-Za-z0-9._-]', "_", name.encode("ascii", "replace").decode())[:100] or "fichier"
    return Response(data, media_type="application/octet-stream",
                    headers={"Content-Disposition": f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{_pct(name)}",
                             "X-Content-Type-Options": "nosniff", "Cache-Control": "no-store"})

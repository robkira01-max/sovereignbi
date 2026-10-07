"""Routes de gestion des organisations (multi-tenant)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.security.rbac import RequireRole

router = APIRouter(prefix="/orgs", tags=["orgs"])

_ADMIN = RequireRole("admin")
_VIEWER = RequireRole("viewer")


class CreateOrgRequest(BaseModel):
    name: str


class AddMemberRequest(BaseModel):
    key: str


def _get_registry(request: Request):
    return request.app.state.org_registry


@router.post("", status_code=201)
def create_org(
    body: CreateOrgRequest,
    request: Request,
    api_key: str = Depends(_ADMIN),
):
    registry = _get_registry(request)
    org = registry.create(name=body.name, owner_key=api_key)
    return {"org_id": org.org_id, "name": org.name, "owner_key": org.owner_key, "created_at": org.created_at}


@router.get("")
def list_orgs(
    request: Request,
    api_key: str = Depends(_VIEWER),
):
    registry = _get_registry(request)
    orgs = registry.list_orgs(api_key)
    return {"orgs": [{"org_id": o.org_id, "name": o.name, "member_count": len(o.member_keys)} for o in orgs]}


@router.get("/{org_id}")
def get_org(
    org_id: str,
    request: Request,
    api_key: str = Depends(_VIEWER),
):
    registry = _get_registry(request)
    org = registry.get(org_id)
    if org is None or not org.has_access(api_key):
        raise HTTPException(404, "Organisation introuvable.")
    return {
        "org_id": org.org_id,
        "name": org.name,
        "owner_key": org.owner_key,
        "member_keys": org.member_keys,
        "created_at": org.created_at,
    }


@router.post("/{org_id}/members", status_code=200)
def add_member(
    org_id: str,
    body: AddMemberRequest,
    request: Request,
    api_key: str = Depends(_ADMIN),
):
    registry = _get_registry(request)
    try:
        org = registry.add_member(org_id, body.key, api_key)
    except KeyError as e:
        raise HTTPException(404, str(e))
    except PermissionError as e:
        raise HTTPException(403, str(e))
    return {"org_id": org.org_id, "member_keys": org.member_keys}


@router.delete("/{org_id}/members/{key}", status_code=200)
def remove_member(
    org_id: str,
    key: str,
    request: Request,
    api_key: str = Depends(_ADMIN),
):
    registry = _get_registry(request)
    try:
        org = registry.remove_member(org_id, key, api_key)
    except KeyError as e:
        raise HTTPException(404, str(e))
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"org_id": org.org_id, "member_keys": org.member_keys}

"""Gestion des clés API personnelles (P-083). Toutes les routes exigent une SESSION nominative.

Le propriétaire crée, liste, fait tourner et révoque SES clés ; un administrateur peut seulement révoquer (et lister)
celles des autres, afin que l'attribution d'une clé à sa personne ne se perde jamais. La clé en clair n'apparaît
qu'une fois, dans la réponse de création ou de rotation.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from app.auth import apikeys
from app.auth.apikeys import KeyError_
from app.feedback import record_audit
from app.security import legacy_keys
from app.security.identity import current_identity
from app.security.rbac import RequireRole

router = APIRouter(prefix="/auth/keys", tags=["api-keys"])
_SESSION = RequireRole("viewer", session_only=False)
_ADMIN_SESSION = RequireRole("admin")


class KeyCreate(BaseModel):
    label: str = Field(default="", max_length=80)
    ttl_days: int = Field(default=apikeys.DEFAULT_TTL_DAYS, ge=1, le=apikeys.MAX_TTL_DAYS)


class KeyRevoke(BaseModel):
    reason: str = Field(default="", max_length=200)


def _me(_role: str = Depends(_SESSION)) -> int:
    ident = current_identity.get()
    if ident is None or ident.method != "session" or ident.user_id is None:
        raise HTTPException(403, "La gestion des clés exige une session nominative (connexion), pas une clé API.")
    return ident.user_id


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"          # la réponse de création contient la clé en clair


def _audit(action: str, **details) -> None:
    try:
        record_audit(action, details)           # jamais la clé : identifiants et préfixe non secret seulement
    except OSError:
        pass


@router.post("", status_code=201)
def create_key(body: KeyCreate, response: Response, uid: int = Depends(_me)) -> dict:
    _no_store(response)
    try:
        rec, raw = apikeys.create_key(uid, body.label, body.ttl_days)
    except KeyError_ as e:
        raise HTTPException(422, str(e)) from None
    _audit("api_key_created", user_id=uid, target_key_id=rec["id"], key_ref=rec["key_prefix"], expires_at=rec["expires_at"])
    return {**rec, "key": raw, "notice": "Copiez cette clé maintenant : elle ne sera plus jamais affichée."}


@router.get("")
def list_my_keys(uid: int = Depends(_me)) -> list[dict]:
    return apikeys.list_keys(uid)


@router.get("/all")
def list_all_keys(_: str = Depends(_ADMIN_SESSION), uid: int = Depends(_me)) -> list[dict]:
    return apikeys.list_keys(None)


@router.get("/legacy-status")
def legacy_status(_: str = Depends(_ADMIN_SESSION), uid: int = Depends(_me)) -> dict:
    return legacy_keys.status()


@router.delete("/{key_id}")
def revoke(key_id: int, response: Response, body: KeyRevoke | None = None, uid: int = Depends(_me)) -> dict:
    _no_store(response)
    ident = current_identity.get()
    rec = apikeys.get_key(key_id)
    # Même réponse pour « inexistante » et « celle d'un autre » : pas d'énumération par un non-administrateur.
    if rec is None or (rec["user_id"] != uid and (ident is None or ident.role != "admin")):
        raise HTTPException(404, "Clé introuvable.")
    out = apikeys.revoke_key(key_id, uid, (body.reason if body else ""))
    _audit("api_key_revoked", user_id=rec["user_id"], target_key_id=key_id, key_ref=rec["key_prefix"], revoked_by=uid,
           by_owner=rec["user_id"] == uid)
    return out


@router.post("/{key_id}/rotate", status_code=201)
def rotate(key_id: int, response: Response, uid: int = Depends(_me)) -> dict:
    """Crée une nouvelle clé (mêmes libellé et durée) puis révoque l'ancienne. Seul le propriétaire fait tourner sa clé."""
    _no_store(response)
    old = apikeys.get_key(key_id)
    if old is None or old["user_id"] != uid:
        raise HTTPException(404, "Clé introuvable.")
    from datetime import datetime
    ttl = max(1, min(apikeys.MAX_TTL_DAYS, (datetime.fromisoformat(old["expires_at"]) - datetime.fromisoformat(old["created_at"])).days or 1))
    try:
        rec, raw = apikeys.create_key(uid, old["label"], ttl)
    except KeyError_ as e:
        raise HTTPException(422, str(e)) from None
    apikeys.revoke_key(key_id, uid, "rotation")
    _audit("api_key_rotated", user_id=uid, old_key_id=key_id, target_key_id=rec["id"], key_ref=rec["key_prefix"])
    return {**rec, "key": raw, "notice": "Copiez cette clé maintenant : elle ne sera plus jamais affichée."}

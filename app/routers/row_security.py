"""Administration de la sécurité par ligne (P-068) : règles (lecture) et périmètres des comptes. Admin seulement."""
from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.auth import security as sec
from app.feedback import record_audit
from app.security import row_policy
from app.security.rbac import RequireRole

router = APIRouter(prefix="/security", tags=["security"])
_ADMIN = RequireRole("admin")
log = structlog.get_logger()


def _audit(action: str, **details) -> None:
    try:
        record_audit(action, details)
    except OSError:
        log.error("audit_write_failed", action=action)


@router.get("/row-policies")
def row_policies(request: Request, _: str = Depends(_ADMIN)):
    """Règles actives et diagnostic : table/colonne présentes dans la base chargée ?"""
    try:
        pols = row_policy.load_policies()
    except row_policy.RowPolicyError as e:
        return {"active": True, "valid": False, "error": str(e), "policies": [],
                "note": "Fichier invalide : toutes les tables protégées sont refusées tant qu'il n'est pas corrigé."}
    store = request.app.state.store
    out = []
    for p in pols:
        problem = None
        if p.table not in {t.lower() for t in store.tables}:
            problem = "table absente de la base chargée"
        else:
            cols = {r[0].lower() for r in store.con.execute(
                "SELECT column_name FROM information_schema.columns WHERE lower(table_name)=?", [p.table]).fetchall()}
            if p.column.lower() not in cols:
                problem = "colonne introuvable"
        out.append({"table": p.table, "column": p.column, "scope": p.scope, "problem": problem})
    return {"active": bool(pols), "valid": True, "policies": out}


class ScopeBody(BaseModel):
    values: list[str] = Field(max_length=row_policy.MAX_VALUES_PER_SCOPE)


@router.get("/users/{user_id}/scopes")
def get_scopes(user_id: int, _: str = Depends(_ADMIN)):
    if sec.get_user(user_id) is None:
        raise HTTPException(404, "Compte introuvable.")
    return {"user_id": user_id, "scopes": row_policy.get_scopes(user_id)}


@router.put("/users/{user_id}/scopes/{scope}")
def put_scope(user_id: int, scope: str, body: ScopeBody, _: str = Depends(_ADMIN)):
    """Remplace les valeurs d'un périmètre (liste vide = retire le périmètre, donc accès refusé aux tables concernées)."""
    if sec.get_user(user_id) is None:
        raise HTTPException(404, "Compte introuvable.")
    try:
        n = row_policy.set_scope(user_id, scope, body.values)
    except row_policy.RowPolicyError as e:
        raise HTTPException(422, str(e)) from None
    _audit("scope_updated", user_id=user_id, scope=scope, values=n)
    return {"user_id": user_id, "scope": scope, "values": n}

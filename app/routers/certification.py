"""Jeux de données certifiés (P-069). Émission/révocation : admin ; consultation : viewer."""
from __future__ import annotations

from dataclasses import asdict

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.certification import registry
from app.feedback import record_audit
from app.security.rbac import RequireRole

router = APIRouter(prefix="/certification", tags=["certification"])
_VIEWER, _ADMIN = RequireRole("viewer"), RequireRole("admin")
log = structlog.get_logger()

DISCLAIMER = ("Validation enregistrée par un administrateur de ce serveur ; MizanBI ne vérifie pas l'institution. "
              "La pastille tombe dès que les données changent.")


def _audit(action: str, **details) -> None:
    try:
        record_audit(action, details)
    except OSError:
        log.error("audit_write_failed", action=action)


def _actor(request: Request) -> str:
    from app.security.identity import current_identity
    ident = current_identity.get()
    return ident.actor if ident else "unknown"


class CertifyBody(BaseModel):
    table: str = Field(max_length=64)
    certifier: str = Field(max_length=120, description="Institution qui a validé, ex. INSTAD")
    reference: str = Field(max_length=300, description="Décision, note ou courriel de validation")
    valid_until: str | None = Field(None, max_length=40)


class RevokeBody(BaseModel):
    reason: str = Field(max_length=300)


@router.post("", status_code=201)
def certify(body: CertifyBody, request: Request, _: str = Depends(_ADMIN)):
    try:
        c = registry.certify(request.app.state.store, body.table, body.certifier, body.reference,
                             recorded_by=_actor(request), valid_until=body.valid_until)
    except registry.CertificationError as e:
        raise HTTPException(422, str(e)) from None
    _audit("dataset_certified", certification_id=c.id, table=c.table, actor=c.recorded_by)
    return {**asdict(c), "disclaimer": DISCLAIMER}


@router.post("/{cert_id}/revoke")
def revoke(cert_id: str, body: RevokeBody, request: Request, _: str = Depends(_ADMIN)):
    try:
        c = registry.revoke(cert_id, body.reason)
    except KeyError:
        raise HTTPException(404, "Certification introuvable.") from None
    except registry.CertificationError as e:
        raise HTTPException(422, str(e)) from None
    _audit("dataset_certification_revoked", certification_id=cert_id, table=c.table, actor=_actor(request))
    return asdict(c)


@router.get("")
def list_status(request: Request, _: str = Depends(_VIEWER)):
    """Pastille de chaque table chargée (sans donnée de ligne)."""
    store = request.app.state.store
    try:
        items = [registry.status(store, t) for t in sorted(store.tables)]
    except registry.CertificationError as e:
        raise HTTPException(500, str(e)) from None
    return {"disclaimer": DISCLAIMER, "tables": items}


@router.get("/{table}")
def table_status(table: str, request: Request, _: str = Depends(_VIEWER)):
    try:
        return {**registry.status(request.app.state.store, table), "disclaimer": DISCLAIMER}
    except registry.CertificationError as e:
        raise HTTPException(500, str(e)) from None


@router.get("/{table}/history")
def table_history(table: str, _: str = Depends(_ADMIN)):
    return {"table": table, "history": [asdict(c) for c in registry.history(table)]}

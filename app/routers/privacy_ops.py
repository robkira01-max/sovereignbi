"""Export/suppression de compte et registre d'incidents (P-064). Administrateur seulement."""
from __future__ import annotations

from dataclasses import asdict

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.compliance import account_data, incidents
from app.feedback import record_audit
from app.security.rbac import RequireRole

router = APIRouter(prefix="/compliance", tags=["compliance"])
_ADMIN = RequireRole("admin")
log = structlog.get_logger()


def _audit(action: str, **details) -> None:
    try:
        record_audit(action, details)                 # identifiants numériques seulement, jamais d'e-mail
    except OSError:
        log.error("audit_write_failed", action=action)


@router.get("/account/{user_id}/export")
def export_account(user_id: int, _: str = Depends(_ADMIN)):
    try:
        data = account_data.export_account(user_id)
    except account_data.AccountError as e:
        raise HTTPException(404 if "introuvable" in str(e) else 422, str(e)) from None
    _audit("account_exported", user_id=user_id)
    return data


@router.delete("/account/{user_id}")
def erase_account(user_id: int, confirm: str = Query(max_length=254, description="Adresse exacte du compte"),
                  _: str = Depends(_ADMIN)):
    try:
        result = account_data.erase_account(user_id, confirm)
    except account_data.AccountError as e:
        raise HTTPException(404 if "introuvable" in str(e) else 409, str(e)) from None
    _audit("account_erased", **result)
    return result


class IncidentCreate(BaseModel):
    detected_at: str = Field(max_length=40)
    severity: str
    category: str = Field(max_length=80)
    description: str = Field(max_length=2000, description="Sans donnée personnelle")
    personal_data_involved: bool


class IncidentUpdate(BaseModel):
    status: str | None = None
    action: str | None = Field(None, max_length=500)
    clients_notified_at: str | None = Field(None, max_length=40)
    authority_notified_at: str | None = Field(None, max_length=40)


@router.post("/incidents", status_code=201)
def open_incident(body: IncidentCreate, _: str = Depends(_ADMIN)):
    try:
        inc = incidents.open_incident(**body.model_dump())
    except incidents.RegisterCorruptError as e:
        raise HTTPException(500, str(e)) from None
    except incidents.IncidentError as e:
        raise HTTPException(422, str(e)) from None
    _audit("incident_opened", incident_id=inc.id, severity=inc.severity)
    return asdict(inc)


@router.get("/incidents")
def list_incidents(status: str | None = Query(None, max_length=20), _: str = Depends(_ADMIN)):
    try:
        items = incidents.list_incidents(status)
    except incidents.IncidentError as e:
        raise HTTPException(500, str(e)) from None
    return {"count": len(items), "overdue_notifications": [i.id for i in incidents.overdue_notifications()],
            "incidents": [asdict(i) for i in items]}


@router.put("/incidents/{incident_id}")
def update_incident(incident_id: str, body: IncidentUpdate, _: str = Depends(_ADMIN)):
    try:
        inc = incidents.update_incident(incident_id, **body.model_dump())
    except KeyError:
        raise HTTPException(404, "Incident introuvable.") from None
    except incidents.RegisterCorruptError as e:
        raise HTTPException(500, str(e)) from None
    except incidents.IncidentError as e:
        raise HTTPException(422, str(e)) from None
    _audit("incident_updated", incident_id=incident_id, status=inc.status)
    return asdict(inc)

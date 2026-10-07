"""Routes de conformité Loi 25 / PIPEDA."""
from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.compliance.models import (
    add_inventory_item,
    create_subject_request,
    list_consents,
    list_inventory,
    list_requests,
    record_consent,
    update_request_status,
    withdraw_consent,
)
from app.security.rbac import RequireRole

router = APIRouter(prefix="/compliance", tags=["compliance"])

_VIEWER = RequireRole("viewer")
_EDITOR = RequireRole("editor")
_ADMIN = RequireRole("admin")


class ConsentRequest(BaseModel):
    user_id: str
    purpose: str
    granted: bool
    ip_address: str | None = None


class WithdrawRequest(BaseModel):
    user_id: str
    purpose: str


class SubjectRequestCreate(BaseModel):
    user_id: str
    request_type: str
    notes: str = ""


class RequestStatusUpdate(BaseModel):
    status: str
    notes: str = ""


class InventoryItemCreate(BaseModel):
    data_category: str
    description: str
    retention_policy: str
    legal_basis: str
    location: str


@router.post("/consent")
def record_user_consent(body: ConsentRequest, _: str = Depends(_EDITOR)):
    c = record_consent(
        user_id=body.user_id,
        purpose=body.purpose,
        granted=body.granted,
        ip_address=body.ip_address,
    )
    return asdict(c)


@router.delete("/consent")
def withdraw_user_consent(body: WithdrawRequest, _: str = Depends(_EDITOR)):
    count = withdraw_consent(user_id=body.user_id, purpose=body.purpose)
    return {"withdrawn": count}


@router.get("/consent/{user_id}")
def get_user_consents(user_id: str, _: str = Depends(_VIEWER)):
    return [asdict(c) for c in list_consents(user_id)]


@router.post("/requests")
def create_dsr(body: SubjectRequestCreate, _: str = Depends(_VIEWER)):
    try:
        r = create_subject_request(
            user_id=body.user_id,
            request_type=body.request_type,
            notes=body.notes,
        )
        return asdict(r)
    except ValueError as e:
        raise HTTPException(422, str(e))


@router.get("/requests")
def list_dsrs(
    user_id: str | None = Query(default=None),
    _: str = Depends(_ADMIN),
):
    return [asdict(r) for r in list_requests(user_id=user_id)]


@router.put("/requests/{request_id}")
def update_dsr(request_id: str, body: RequestStatusUpdate, _: str = Depends(_ADMIN)):
    try:
        r = update_request_status(request_id, body.status, body.notes)  # type: ignore[arg-type]
        return asdict(r)
    except KeyError:
        raise HTTPException(404, "Demande introuvable")
    except ValueError as e:
        raise HTTPException(422, str(e))


@router.post("/inventory")
def add_data_inventory(body: InventoryItemCreate, _: str = Depends(_ADMIN)):
    try:
        item = add_inventory_item(
            data_category=body.data_category,
            description=body.description,
            retention_policy=body.retention_policy,  # type: ignore[arg-type]
            legal_basis=body.legal_basis,
            location=body.location,
        )
        return asdict(item)
    except ValueError as e:
        raise HTTPException(422, str(e))


@router.get("/inventory")
def get_data_inventory(_: str = Depends(_VIEWER)):
    return [asdict(i) for i in list_inventory()]


@router.get("/notice")
def privacy_notice(_: str = Depends(_VIEWER)):
    """Retourne l'avis de confidentialité en JSON (Loi 25 / PIPEDA)."""
    return {
        "title": "Avis de confidentialité — SovereignBI",
        "version": "1.0",
        "applicable_laws": ["Loi 25 (Québec)", "PIPEDA (Canada)"],
        "data_controller": "Opérateur de SovereignBI",
        "data_location": "Infrastructure locale de l'opérateur — aucune donnée transmise à des tiers",
        "purposes": [
            {"id": "analytics", "description": "Analyse des données chargées par l'utilisateur"},
            {"id": "ai_processing", "description": "Traitement IA local (Ollama, aucun modèle externe)"},
        ],
        "retention": "Selon la politique de rétention configurée par l'opérateur",
        "rights": ["accès", "rectification", "suppression", "exportation", "retrait du consentement"],
        "contact": "Adressez vos demandes à l'opérateur de l'instance SovereignBI",
        "disclaimer": "Cet outil est réservé à un usage professionnel. Il ne constitue pas un conseil juridique.",
    }

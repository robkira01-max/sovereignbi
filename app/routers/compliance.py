"""Routes de conformité Loi 25 / PIPEDA."""
from __future__ import annotations

from dataclasses import asdict

import os

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field

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


class SelfConsentRequest(BaseModel):
    # Allowlist: "<document>:<YYYY-MM>" — pas de finalité libre écrite par le client.
    purpose: str = Field(pattern=r"^(cgu|privacy):[0-9]{4}-[0-9]{2}$")
    granted: bool = True


@router.post("/consent/self")
def record_self_consent(
    body: SelfConsentRequest,
    _: str = Depends(_VIEWER),
    authorization: str | None = Header(default=None),
):
    """Enregistre l'acceptation des CGU / de la politique par l'utilisateur connecté.

    L'identité vient de la session (jamais du corps de la requête) : un utilisateur
    ne peut enregistrer un consentement qu'en son propre nom. Une clé API n'a pas
    d'identité utilisateur, elle est refusée ici. L'adresse IP n'est pas conservée.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(400, "Session utilisateur requise (connexion par email).")
    from app.auth.security import verify_session  # lazy to avoid circular

    user = verify_session(authorization[7:])
    if not user:
        raise HTTPException(401, "Session expirée ou invalide.")
    c = record_consent(user_id=user["email"], purpose=body.purpose, granted=body.granted)
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


def _ai_processing() -> tuple[str, str]:
    """(description du traitement IA, localisation des données) selon LLM_PROVIDER."""
    from app import ai_policy

    provider = os.environ.get("LLM_PROVIDER", "ollama").lower()
    if provider == "ollama":
        return (
            "Traitement IA local (Ollama, aucun modèle externe)",
            "Infrastructure de l'opérateur — aucune donnée transmise à des tiers",
        )
    if ai_policy.strict():
        return (
            f"Traitement IA par un fournisseur externe ({provider}) en mode strict : seules la question, les noms de "
            "tables et de colonnes et le modèle sémantique lui sont transmis — aucune ligne de données, aucun résultat, "
            "aucun extrait de document",
            "Infrastructure de l'opérateur ; les questions et le schéma sont transmis au fournisseur externe configuré",
        )
    return (
        f"Traitement IA par un fournisseur externe ({provider}) : les questions et extraits de données "
        "nécessaires à la réponse lui sont transmis",
        "Infrastructure de l'opérateur ; les requêtes IA sont transmises au fournisseur externe configuré",
    )


@router.get("/notice")
def privacy_notice(_: str = Depends(_VIEWER)):
    from app.ai_policy import strict as ai_strict

    """Retourne l'avis de confidentialité en JSON (Loi 25 / PIPEDA)."""
    ai_description, data_location = _ai_processing()
    return {
        "title": "Avis de confidentialité — MizanBI",
        "version": "1.1",
        "applicable_laws": ["Loi 25 (Québec)", "PIPEDA (Canada)"],
        "data_controller": "Opérateur de MizanBI",
        "data_location": data_location,
        "purposes": [
            {"id": "analytics", "description": "Analyse des données chargées par l'utilisateur"},
            {"id": "ai_processing", "description": ai_description},
        ],
        "ai_strict_mode": ai_strict(),
        "retention": "Selon la politique de rétention configurée par l'opérateur",
        "rights": ["accès", "rectification", "suppression", "exportation", "retrait du consentement"],
        "contact": "Adressez vos demandes à l'opérateur de l'instance MizanBI",
        "disclaimer": "Cet outil est réservé à un usage professionnel. Il ne constitue pas un conseil juridique.",
    }

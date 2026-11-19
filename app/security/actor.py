"""Identité de l'acteur et écriture d'audit, partagées par les routeurs du pack Audit (P-073, P-074).

- `actor_label` : « user:<id> » pour une session, « api_key:<rôle> » pour une clé (une clé n'est pas une personne :
  on distingue au moins le rôle). Jamais la clé elle-même.
- `audit_soft` : refus et consultations ; une panne du journal est consignée mais ne bloque pas.
- `audit_strict` : action sensible (écriture) ; si le journal est inscriptible nulle part, on refuse (échec fermé, 503).
"""
from __future__ import annotations

import structlog
from fastapi import HTTPException, Request

from app.feedback import record_audit

log = structlog.get_logger()


def actor_label(request: Request, role: str) -> str:
    if request.headers.get("x-api-key"):
        return f"api_key:{role}"
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        from app.auth.security import verify_session
        u = verify_session(auth[7:])
        if u:
            return f"user:{u['id']}"
    return "unknown"


def audit_soft(action: str, **details) -> None:
    try:
        record_audit(action, details)
    except OSError:
        log.error("audit_write_failed", action=action)


def audit_strict(action: str, **details) -> None:
    if details.get("actor") == "unknown":      # session expirée entre-temps : pas d'action sensible sans acteur identifié
        raise HTTPException(401, "Session expirée : reconnectez-vous.")
    try:
        record_audit(action, details)
    except OSError:
        log.error("audit_write_failed", action=action)
        raise HTTPException(503, "Journal d'audit indisponible : action non enregistrée, donc refusée.") from None

"""Vérification d'intégrité du journal d'audit (P-071). Administrateur seulement."""
from __future__ import annotations

from dataclasses import asdict

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query

from app import feedback
from app.security.rbac import RequireRole

router = APIRouter(prefix="/audit", tags=["audit"])
_ADMIN = RequireRole("admin")
log = structlog.get_logger()

LIMITS = ("Cette vérification détecte une entrée modifiée, supprimée au milieu ou insérée. Elle ne détecte pas la "
          "suppression des dernières entrées sans ancrage (notez `entries` et `head` hors du serveur, puis repassez-les "
          "en `anchor_entries` / `anchor_hash`), ni une réécriture complète par quelqu'un qui peut écrire le fichier : "
          "la chaîne n'est pas signée par un secret.")


@router.get("/verify")
def verify(
    anchor_entries: int | None = Query(None, ge=0, le=10_000_000, description="Nombre d'entrées noté lors d'une vérification précédente"),
    anchor_hash: str | None = Query(None, min_length=0, max_length=64, pattern="^[0-9a-f]{0,64}$",
                                    description="Empreinte `head` notée avec ce nombre d'entrées"),
    _: str = Depends(_ADMIN),
):
    if (anchor_entries is not None and anchor_entries > 0) != bool(anchor_hash):
        raise HTTPException(422, "anchor_entries (> 0) et anchor_hash vont ensemble.")
    result = feedback.verify_audit_chain(anchor_entries=anchor_entries, anchor_hash=anchor_hash)
    try:   # méta-audit : qui a vérifié, avec quel résultat (jamais le contenu des entrées)
        feedback.record_audit("audit_verified", {"valid": result.valid, "entries": result.entries})
    except OSError:
        log.error("audit_write_failed", action="audit_verified")
    return {**asdict(result), "limits": LIMITS}

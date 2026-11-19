"""Contrôles d'audit (P-075) : liste des règles, exécution sur un document importé, signalements.

Vocabulaire : « signal de risque à examiner », jamais « fraude ». Un signalement n'est pas une conclusion.
Rôles : règles = viewer ; exécution et lecture des signalements = editor (contenu dérivé des données) ; avec des règles
de sécurité par ligne actives, réservé à l'admin (les signalements citent montants et comptes de tout le document).
"""
from __future__ import annotations

import json
import threading
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator

from app.audit_data import repo
from app.audit_rules import engine, store as rstore
from app.audit_rules.registry import RuleError, get_registry
from app.security import row_policy
from app.security.actor import actor_label, audit_soft, audit_strict
from app.security.rbac import RequireRole

_RUN_SLOT = threading.Lock()      # un seul contrôle à la fois : la connexion DuckDB est partagée
router = APIRouter(prefix="/audit-rules", tags=["audit-rules"])
_VIEWER, _EDITOR = RequireRole("viewer"), RequireRole("editor")
DISCLAIMER = ("Ces signalements sont des signaux de risque à examiner, pas des conclusions : seule l'analyse des pièces "
              "par une personne qualifiée permet de conclure.")


class RunBody(BaseModel):
    document_id: str = Field(min_length=36, max_length=36)
    rules: list[str] | None = Field(None, max_length=20)
    params: dict[str, dict] = Field(default_factory=dict, max_length=20)

    @field_validator("params")
    @classmethod
    def _bounded(cls, v):
        if len(json.dumps(v, default=str)) > 20_000:
            raise ValueError("paramètres trop volumineux")
        return v


def _registry():
    try:
        return get_registry()
    except RuleError as e:
        raise HTTPException(503, f"Règles d'audit indisponibles : {e}") from None


def _guard(role: str) -> None:
    if role != "admin" and row_policy.active():
        raise HTTPException(403, "Des règles de sécurité par ligne sont actives : les contrôles d'audit sont réservés à un administrateur.")


@router.get("/rules")
def list_rules(_: str = Depends(_VIEWER)):
    reg = _registry()
    return {"ruleset_hash": reg.ruleset_hash(), "rules": [r.public() for r in reg.rules.values()], "disclaimer": DISCLAIMER}


@router.post("/runs", status_code=201)
def run_checks(body: RunBody, request: Request, role: str = Depends(_EDITOR)):
    _guard(role)
    store, actor, reg = request.app.state.store, actor_label(request, role), _registry()
    doc = repo.get_document(store, body.document_id)
    if doc is None:
        raise HTTPException(404, "Document introuvable.")
    if doc["status"] != "imported":
        raise HTTPException(409, "Le document doit d'abord être importé (P-074).")
    if not _RUN_SLOT.acquire(blocking=False):
        raise HTTPException(429, "Un contrôle est déjà en cours : réessayez dans un instant.")
    try:
        outcomes = engine.run_rules(store, reg, doc, body.params, body.rules)
    except KeyError:
        raise HTTPException(422, "Règle inconnue.") from None
    finally:
        _RUN_SLOT.release()
    run_id = rstore.new_run_id()
    summary = {"ruleset_hash": reg.ruleset_hash(), "rules": [
        {"code": o.code, "version": o.version, "status": o.status, "reason": o.reason, "findings": len(o.findings),
         "truncated": o.truncated, "params": o.params} for o in outcomes],
        "rows_excluded_for_errors": int(store.execute(
            f"SELECT count(*) FROM {repo.RECORDS} WHERE document_id = '{body.document_id}' AND has_error = TRUE")[1][0][0])}
    total = sum(len(o.findings) for o in outcomes)
    audit_strict("audit_rules_run", run_id=run_id, document_id=body.document_id, ruleset_hash=reg.ruleset_hash(),
                 rules=[o.code for o in outcomes], findings=total, actor=actor)
    with repo.LOCK:
        rstore.save_run(store, run_id=run_id, doc=doc, created_by=actor, ruleset_hash=reg.ruleset_hash(), summary=summary,
                        findings=[(reg.rules[o.code], f) for o in outcomes for f in o.findings])
    return {"run_id": run_id, "document_id": body.document_id, "summary": summary, "findings_total": total, "disclaimer": DISCLAIMER}


@router.get("/runs/{run_id}")
def get_run(run_id: str, request: Request, role: str = Depends(_EDITOR)):
    _guard(role)
    run = rstore.get_run(request.app.state.store, run_id, actor=actor_label(request, role), is_admin=role == "admin")
    if run is None:
        raise HTTPException(404, "Exécution introuvable.")
    return {**run, "disclaimer": DISCLAIMER}


@router.get("/runs/{run_id}/findings")
def get_findings(run_id: str, request: Request, rule_code: str | None = Query(None, max_length=6),
                 severity: Literal["info", "warning"] | None = Query(None), limit: int = Query(100, ge=1, le=500),
                 offset: int = Query(0, ge=0), role: str = Depends(_EDITOR)):
    _guard(role)
    store = request.app.state.store
    if rstore.get_run(store, run_id, actor=actor_label(request, role), is_admin=role == "admin") is None:
        raise HTTPException(404, "Exécution introuvable.")
    audit_soft("audit_findings_read", run_id=run_id, actor=actor_label(request, role))
    return {"findings": rstore.list_findings(store, run_id, rule_code=rule_code, severity=severity, limit=limit, offset=offset),
            "disclaimer": DISCLAIMER}

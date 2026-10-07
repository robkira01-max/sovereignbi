"""Routes d'administration : modèle sémantique, propositions de règles, versionnage.

Auth : en-tête X-Admin-Key comparé à SOVEREIGN_ADMIN_KEY (env).
Si la variable est absente, les routes retournent 503 (service non configuré).
"""
from __future__ import annotations

import dataclasses
import os
from pathlib import Path

import yaml
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from app.semantic.model import SemanticModel, load_model

_YAML_PATH = Path("semantic/model.yaml")
_KEY_HEADER = APIKeyHeader(name="X-Admin-Key", auto_error=False)

router = APIRouter(prefix="/admin", tags=["admin"])


def _require_admin(key: str | None = Depends(_KEY_HEADER)) -> None:
    expected = os.environ.get("SOVEREIGN_ADMIN_KEY", "")
    if not expected:
        raise HTTPException(503, "SOVEREIGN_ADMIN_KEY non configuré")
    if key != expected:
        raise HTTPException(403, "Clé d'administration invalide")


def _load() -> SemanticModel:
    return load_model(_YAML_PATH)


@router.get("/semantic")
def get_semantic(_=Depends(_require_admin)):
    """Retourne le modèle sémantique complet (YAML parsé en JSON)."""
    m = _load()
    return {
        "schema_version": m.schema_version,
        "tables": [
            {
                "name": t.name,
                "description": t.description,
                "columns": [
                    {"name": c.name, "type": c.type, "description": c.description}
                    for c in t.columns
                ],
            }
            for t in m.tables
        ],
        "metrics": [
            {
                "name": me.name,
                "aliases": me.aliases,
                "sql": me.sql,
                "tables": me.tables,
                "description": me.description,
                "join_required": me.join_required,
            }
            for me in m.metrics
        ],
        "joins": [
            {"from_table": j.from_table, "to_table": j.to_table, "on": j.on, "type": j.type}
            for j in m.joins
        ],
        "rules": m.rules,
        "glossary": m.glossary,
    }


@router.put("/semantic")
def put_semantic(body: dict, _=Depends(_require_admin)):
    """Remplace le fichier semantic/model.yaml par le contenu fourni."""
    if "schema_version" not in body:
        raise HTTPException(422, "schema_version requis")
    _YAML_PATH.parent.mkdir(parents=True, exist_ok=True)
    _YAML_PATH.write_text(yaml.dump(body, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return {"saved": True, "path": str(_YAML_PATH)}


@router.get("/semantic/tables")
def get_tables(_=Depends(_require_admin)):
    """Liste les tables du modèle sémantique."""
    m = _load()
    return [
        {"name": t.name, "description": t.description, "column_count": len(t.columns)}
        for t in m.tables
    ]


@router.get("/semantic/metrics")
def get_metrics(_=Depends(_require_admin)):
    """Liste les métriques calculées définies dans le modèle."""
    m = _load()
    return [
        {
            "name": me.name,
            "aliases": me.aliases,
            "sql": me.sql,
            "join_required": me.join_required,
        }
        for me in m.metrics
    ]


# ── Learning routes ───────────────────────────────────────────────────────────


class SnapshotRequest(BaseModel):
    label: str = ""


class RollbackRequest(BaseModel):
    version: str


@router.get("/report")
def get_report(_=Depends(_require_admin)):
    """Generate the weekly error report from feedback data."""
    from app.feedback import load_feedback
    from app.learning.error_reporter import analyze_errors, format_report_markdown

    entries = load_feedback()
    report = analyze_errors(entries, days=7)
    return {**dataclasses.asdict(report), "markdown": format_report_markdown(report)}


@router.get("/proposals")
def list_proposals(status: str | None = None, _=Depends(_require_admin)):
    """List rule proposals (optional ?status=pending|approved|rejected)."""
    from app.learning.rule_proposer import load_proposals

    proposals = load_proposals(status=status)
    return [dataclasses.asdict(p) for p in proposals]


@router.post("/proposals/apply")
def apply_proposals(_=Depends(_require_admin)):
    """Apply all approved proposals as rules in model.yaml (snapshot first)."""
    from app.learning.rule_proposer import apply_approved_rules

    added = apply_approved_rules()
    return {"applied": len(added), "rules": added}


@router.post("/proposals/{proposal_id}/approve")
def approve_proposal(
    proposal_id: str,
    x_reviewer: str | None = Header(default=None),
    _=Depends(_require_admin),
):
    """Approve a pending proposal."""
    from app.learning.rule_proposer import approve_proposal as _approve

    reviewer = x_reviewer or "admin"
    try:
        p = _approve(proposal_id, reviewer)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return dataclasses.asdict(p)


@router.post("/proposals/{proposal_id}/reject")
def reject_proposal(
    proposal_id: str,
    x_reviewer: str | None = Header(default=None),
    _=Depends(_require_admin),
):
    """Reject a pending proposal."""
    from app.learning.rule_proposer import reject_proposal as _reject

    reviewer = x_reviewer or "admin"
    try:
        p = _reject(proposal_id, reviewer)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return dataclasses.asdict(p)


@router.get("/versions")
def list_versions(_=Depends(_require_admin)):
    """List available model.yaml snapshots."""
    from app.learning.versioning import list_versions as _list

    return _list()


@router.post("/versions/snapshot")
def create_snapshot(body: SnapshotRequest, _=Depends(_require_admin)):
    """Create a manual snapshot of the current model.yaml."""
    from app.learning.versioning import snapshot

    dest = snapshot(label=body.label)
    return {"snapshot": str(dest)}


@router.post("/versions/rollback")
def rollback_version(body: RollbackRequest, _=Depends(_require_admin)):
    """Rollback model.yaml to a previous version (auto-snapshots current state)."""
    from app.learning.versioning import rollback

    try:
        rollback(body.version)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    return {"rolled_back_to": body.version}

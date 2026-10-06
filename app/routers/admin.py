"""Routes d'administration du modèle sémantique.

Auth : en-tête X-Admin-Key comparé à SOVEREIGN_ADMIN_KEY (env).
Si la variable est absente, les routes retournent 503 (service non configuré).
"""
from __future__ import annotations

import os
from pathlib import Path

import yaml
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import APIKeyHeader

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

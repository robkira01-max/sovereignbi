"""Marketplace de templates — imports/exports JSON, templates vedettes, découverte."""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.templates.catalogue import (
    CATALOGUE_PATH,
    CatalogueEntry,
    _load_catalogue,
    _write_catalogue,
    register_template,
)

MARKETPLACE_SEED_PATH = Path("data/marketplace_featured.json")


FEATURED_TEMPLATES: list[dict] = [
    {
        "template_id": "tmpl-sales-summary",
        "title": "Résumé des ventes",
        "description": "Vue d'ensemble des ventes : total, tendance mensuelle, top produits.",
        "tags": ["ventes", "résumé", "tendance"],
    },
    {
        "template_id": "tmpl-kpi-dashboard",
        "title": "Tableau de bord KPI",
        "description": "KPIs essentiels : revenu, nombre de clients, taux de conversion.",
        "tags": ["kpi", "revenu", "conversion"],
    },
    {
        "template_id": "tmpl-inventory-monitor",
        "title": "Suivi des stocks",
        "description": "Niveau de stock, alertes de rupture, délai de réapprovisionnement.",
        "tags": ["stocks", "alertes", "logistique"],
    },
    {
        "template_id": "tmpl-hr-headcount",
        "title": "Effectifs RH",
        "description": "Répartition des employés par département, ancienneté, turnover.",
        "tags": ["rh", "employés", "turnover"],
    },
    {
        "template_id": "tmpl-finance-cashflow",
        "title": "Flux de trésorerie",
        "description": "Entrées/sorties de trésorerie, solde prévisionnel à 30/60/90j.",
        "tags": ["finance", "trésorerie", "prévision"],
    },
    {
        "template_id": "tmpl-hum-beneficiaries",
        "title": "Tableau de bord bénéficiaires",
        "description": "Bénéficiaires enregistrés par statut, pays d'origine et site (HXL).",
        "tags": ["humanitaire", "bénéficiaires", "unhcr", "hxl"],
    },
    {
        "template_id": "tmpl-hum-distributions",
        "title": "Suivi des distributions humanitaires",
        "description": "Quantités distribuées, couverture, tendance mensuelle (WFP/HXL).",
        "tags": ["humanitaire", "distribution", "wfp", "hxl"],
    },
    {
        "template_id": "tmpl-igad-economy",
        "title": "Tableau de bord économique IGAD",
        "description": "PIB, croissance, IDE des 9 pays de la Corne de l'Afrique (Banque mondiale).",
        "tags": ["igad", "économie", "pib", "afrique-de-l-est"],
    },
    {
        "template_id": "tmpl-igad-food-security",
        "title": "Sécurité alimentaire IGAD (IPC)",
        "description": "Phases IPC et population en crise alimentaire par pays IGAD.",
        "tags": ["igad", "sécurité-alimentaire", "ipc", "wfp"],
    },
]


def seed_featured_templates(catalogue_path: Path = CATALOGUE_PATH) -> list[str]:
    """Register featured templates if not already present. Returns list of IDs seeded."""
    seeded = []
    for tmpl in FEATURED_TEMPLATES:
        entry = register_template(
            template_id=tmpl["template_id"],
            title=tmpl["title"],
            description=tmpl["description"],
            tags=tmpl["tags"],
            catalogue_path=catalogue_path,
        )
        seeded.append(entry.template_id)
    return seeded


def get_featured(catalogue_path: Path = CATALOGUE_PATH) -> list[CatalogueEntry]:
    """Return entries that match the featured template IDs."""
    featured_ids = {t["template_id"] for t in FEATURED_TEMPLATES}
    entries = _load_catalogue(catalogue_path)
    return [entries[tid] for tid in featured_ids if tid in entries]


def export_template_package(
    template_id: str,
    catalogue_path: Path = CATALOGUE_PATH,
) -> dict[str, Any]:
    """Export a template as a portable JSON package."""
    entries = _load_catalogue(catalogue_path)
    if template_id not in entries:
        raise KeyError(template_id)
    entry = entries[template_id]
    return {
        "format": "sovereignbi-template/v1",
        "exported_at": datetime.now(tz=timezone.utc).isoformat(),
        "template": asdict(entry),
    }


def import_template_package(
    package: dict[str, Any],
    catalogue_path: Path = CATALOGUE_PATH,
    force_new_id: bool = True,
) -> CatalogueEntry:
    """Import a template from a JSON package. Creates a new ID if force_new_id."""
    if package.get("format") != "sovereignbi-template/v1":
        raise ValueError("Format de paquet non reconnu. Attendu : 'sovereignbi-template/v1'")
    tmpl = package["template"]
    template_id = str(uuid.uuid4()) if force_new_id else tmpl["template_id"]
    return register_template(
        template_id=template_id,
        title=tmpl["title"],
        description=tmpl.get("description", ""),
        tags=tmpl.get("tags", []),
        catalogue_path=catalogue_path,
    )


def get_trending(
    limit: int = 5,
    catalogue_path: Path = CATALOGUE_PATH,
) -> list[CatalogueEntry]:
    """Return top-N templates by use_count, then rating."""
    from app.templates.catalogue import list_entries
    entries = list_entries(catalogue_path)
    entries.sort(key=lambda e: (-e.use_count, -e.rating))
    return entries[:limit]

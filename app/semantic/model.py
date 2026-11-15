"""Parser du modèle sémantique YAML v2 (rétrocompatible v1)."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class ColumnInfo:
    name: str
    type: str
    description: str
    aliases: list[str] = field(default_factory=list)


@dataclass
class TableInfo:
    name: str
    description: str
    columns: list[ColumnInfo] = field(default_factory=list)


@dataclass
class MetricInfo:
    name: str
    aliases: list[str]
    sql: str
    tables: list[str]
    description: str = ""
    join_required: bool = False
    unit: str = ""
    # Métadonnées d'indicateur (P-066) : tout est facultatif ; `code` rend la mesure publiable (SDMX).
    code: str = ""           # identifiant stable, ex. « PIB_TOTAL » (A-Z, 0-9, _)
    source: str = ""         # producteur ou publication d'origine
    frequency: str = ""      # périodicité SDMX : A, S, Q, M, W, D, H, B, N
    definition: str = ""     # définition statistique
    methodology: str = ""    # méthode de calcul, couverture, exclusions
    topic: str = ""          # thème (économie, démographie…)
    last_updated: str = ""   # date de dernière mise à jour des données (AAAA-MM-JJ)


@dataclass
class FilterInfo:
    """Filtre nommé réutilisable (« ventes confirmées » = statut = 'confirme')."""
    name: str
    sql: str
    aliases: list[str] = field(default_factory=list)
    tables: list[str] = field(default_factory=list)
    description: str = ""


@dataclass
class ValueSynonym:
    """Synonymes d'une valeur de colonne (« QC », « Quebec » → region = 'Québec')."""
    table: str
    column: str
    value: str
    synonyms: list[str] = field(default_factory=list)


@dataclass
class JoinInfo:
    from_table: str
    to_table: str
    on: str
    type: str = "LEFT"


@dataclass
class SemanticModel:
    schema_version: str
    tables: list[TableInfo] = field(default_factory=list)
    metrics: list[MetricInfo] = field(default_factory=list)
    joins: list[JoinInfo] = field(default_factory=list)
    rules: list[str] = field(default_factory=list)
    glossary: list[dict] = field(default_factory=list)
    filters: list[FilterInfo] = field(default_factory=list)
    value_synonyms: list[ValueSynonym] = field(default_factory=list)


def load_model(path: str | Path = "semantic/model.yaml") -> SemanticModel:
    p = Path(path)
    if not p.exists():
        return SemanticModel(schema_version="1")
    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    version = str(raw.get("schema_version", "1"))

    tables = [
        TableInfo(
            name=t["name"],
            description=t.get("description", ""),
            columns=[
                ColumnInfo(
                    name=c["name"],
                    type=c.get("type", "varchar"),
                    description=c.get("description", ""),
                    aliases=list(c.get("aliases", []) or []),
                )
                for c in t.get("columns", [])
            ],
        )
        for t in raw.get("tables", [])
    ]

    metrics = [
        MetricInfo(
            name=m["name"],
            aliases=m.get("aliases", []),
            sql=m["sql"],
            tables=m.get("tables", []),
            description=m.get("description", ""),
            join_required=bool(m.get("join_required", False)),
            unit=str(m.get("unit", "") or ""),
            code=str(m.get("code", "") or ""),
            source=str(m.get("source", "") or ""),
            frequency=str(m.get("frequency", "") or ""),
            definition=str(m.get("definition", "") or ""),
            methodology=str(m.get("methodology", "") or ""),
            topic=str(m.get("topic", "") or ""),
            last_updated=str(m.get("last_updated", "") or ""),
        )
        for m in raw.get("metrics", [])
    ]

    filters = [
        FilterInfo(
            name=f["name"],
            sql=f["sql"],
            aliases=list(f.get("aliases", []) or []),
            tables=list(f.get("tables", []) or []),
            description=f.get("description", ""),
        )
        for f in raw.get("filters", []) or []
    ]

    value_synonyms = [
        ValueSynonym(
            table=v["table"], column=v["column"], value=str(v["value"]),
            synonyms=[str(x) for x in (v.get("synonyms", []) or [])],
        )
        for v in raw.get("value_synonyms", []) or []
    ]

    joins = [
        JoinInfo(
            from_table=j["from_table"],
            to_table=j["to_table"],
            on=j.get("condition", j.get("on", "")),
            type=j.get("type", "LEFT"),
        )
        for j in raw.get("joins", [])
    ]

    return SemanticModel(
        schema_version=version,
        tables=tables,
        metrics=metrics,
        joins=joins,
        rules=raw.get("rules", []),
        glossary=raw.get("glossary", []),
        filters=filters,
        value_synonyms=value_synonyms,
    )


def model_to_prompt_text(model: SemanticModel) -> str:
    """Format texte compact pour injection dans le prompt (fallback sans schema linking)."""
    parts: list[str] = []

    if model.metrics:
        parts.append("Métriques :")
        for m in model.metrics:
            aliases = f" (alias : {', '.join(m.aliases)})" if m.aliases else ""
            unit = f" [{m.unit}]" if m.unit else ""
            parts.append(f"  {m.name}{aliases}{unit} = {m.sql}")

    if model.filters:
        parts.append("Filtres nommés (à utiliser dans WHERE) :")
        for f in model.filters:
            aliases = f" (alias : {', '.join(f.aliases)})" if f.aliases else ""
            parts.append(f"  {f.name}{aliases} : {f.sql}")

    if model.value_synonyms:
        parts.append("Synonymes de valeurs :")
        for v in model.value_synonyms:
            if v.synonyms:
                parts.append(f"  {v.table}.{v.column} = '{v.value}' (aussi : {', '.join(v.synonyms)})")

    if model.tables:
        parts.append("Tables :")
        for t in model.tables:
            col_str = ", ".join(
                (f"{c.name} ({c.description})" if c.description else c.name)
                + (f" [alias : {', '.join(c.aliases)}]" if c.aliases else "")
                for c in t.columns
            )
            parts.append(f"  {t.name} : {col_str}")

    if model.joins:
        parts.append("Jointures :")
        for j in model.joins:
            parts.append(f"  {j.from_table} {j.type} JOIN {j.to_table} ON {j.on}")

    if model.rules:
        parts.append("Règles :")
        for r in model.rules:
            parts.append(f"  - {r}")

    # v1 fallback
    if not model.tables and model.glossary:
        parts.append("Glossaire métier :")
        for g in model.glossary:
            parts.append(f"  - {g.get('terme', '')} : {g.get('definition', '')}")

    return "\n".join(parts)

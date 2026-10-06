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
        )
        for m in raw.get("metrics", [])
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
    )


def model_to_prompt_text(model: SemanticModel) -> str:
    """Format texte compact pour injection dans le prompt (fallback sans schema linking)."""
    parts: list[str] = []

    if model.metrics:
        parts.append("Métriques :")
        for m in model.metrics:
            aliases = f" (alias : {', '.join(m.aliases)})" if m.aliases else ""
            parts.append(f"  {m.name}{aliases} = {m.sql}")

    if model.tables:
        parts.append("Tables :")
        for t in model.tables:
            col_str = ", ".join(
                f"{c.name} ({c.description})" if c.description else c.name
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

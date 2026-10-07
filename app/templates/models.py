"""Full dashboard template model with tiles."""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TEMPLATES_DIR = Path("data/templates")


@dataclass
class DashboardTile:
    tile_id: str
    title: str
    question: str
    chart_type: str  # "kpi", "bar", "line", "pie", "table"
    sql_hint: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "DashboardTile":
        return cls(
            tile_id=d.get("tile_id", str(uuid.uuid4())),
            title=d["title"],
            question=d["question"],
            chart_type=d.get("chart_type", "kpi"),
            sql_hint=d.get("sql_hint", ""),
        )


@dataclass
class DashboardTemplate:
    template_id: str
    title: str
    description: str
    sector: str
    source_format: str
    tiles: list[DashboardTile] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["tiles"] = [t.to_dict() for t in self.tiles]
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "DashboardTemplate":
        tiles = [DashboardTile.from_dict(t) for t in d.get("tiles", [])]
        return cls(
            template_id=d["template_id"],
            title=d["title"],
            description=d.get("description", ""),
            sector=d.get("sector", "général"),
            source_format=d.get("source_format", "manual"),
            tiles=tiles,
            tags=d.get("tags", []),
            created_at=d.get("created_at", ""),
            updated_at=d.get("updated_at", ""),
        )


def save_template(template: DashboardTemplate, base_dir: Path = TEMPLATES_DIR) -> Path:
    base_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(tz=timezone.utc).isoformat()
    if not template.created_at:
        template.created_at = now
    template.updated_at = now
    path = base_dir / f"{template.template_id}.json"
    path.write_text(json.dumps(template.to_dict(), indent=2, ensure_ascii=False))
    return path


def load_template(template_id: str, base_dir: Path = TEMPLATES_DIR) -> DashboardTemplate:
    path = base_dir / f"{template_id}.json"
    if not path.exists():
        raise KeyError(f"Template introuvable : {template_id}")
    return DashboardTemplate.from_dict(json.loads(path.read_text()))


def list_templates(base_dir: Path = TEMPLATES_DIR) -> list[dict[str, Any]]:
    base_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for p in sorted(base_dir.glob("*.json")):
        try:
            t = DashboardTemplate.from_dict(json.loads(p.read_text()))
            results.append({
                "template_id": t.template_id,
                "title": t.title,
                "description": t.description,
                "sector": t.sector,
                "source_format": t.source_format,
                "tiles_count": len(t.tiles),
                "tags": t.tags,
                "created_at": t.created_at,
            })
        except Exception:
            continue
    return results

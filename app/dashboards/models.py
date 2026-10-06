"""Dashboard data models — YAML serialisable."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


@dataclass
class Tile:
    id: str
    type: str  # kpi | line | bar | table | pie
    title: str
    metric: str | None = None
    sql_pinned: str | None = None
    dimensions: list[str] = field(default_factory=list)
    filters: dict[str, Any] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)


@dataclass
class DashboardTheme:
    primary_color: str = "#1f77b4"
    font: str = "sans-serif"
    logo_url: str = ""


@dataclass
class Dashboard:
    id: str
    title: str
    scope: str  # "personal" | "team" | "company"
    tiles: list[Tile]
    theme: DashboardTheme
    created_at: str = ""
    updated_at: str = ""

    @staticmethod
    def now() -> str:
        return datetime.now(timezone.utc).isoformat()


@dataclass
class DashboardTemplate:
    id: str
    title: str
    description: str
    tiles: list[Tile]
    theme: DashboardTheme = field(default_factory=DashboardTheme)


# ─── helpers ─────────────────────────────────────────────────────────────────

def _tile_from_dict(d: dict) -> Tile:
    return Tile(
        id=d["id"],
        type=d["type"],
        title=d["title"],
        metric=d.get("metric"),
        sql_pinned=d.get("sql_pinned"),
        dimensions=d.get("dimensions", []),
        filters=d.get("filters", {}),
        options=d.get("options", {}),
    )


def _theme_from_dict(d: dict | None) -> DashboardTheme:
    if not d:
        return DashboardTheme()
    return DashboardTheme(
        primary_color=d.get("primary_color", "#1f77b4"),
        font=d.get("font", "sans-serif"),
        logo_url=d.get("logo_url", ""),
    )


# ─── Dashboard ────────────────────────────────────────────────────────────────

def save_dashboard(d: Dashboard, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = asdict(d)
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")


def load_dashboard(path: Path) -> Dashboard:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    tiles = [_tile_from_dict(t) for t in data.get("tiles", [])]
    theme = _theme_from_dict(data.get("theme"))
    return Dashboard(
        id=data["id"],
        title=data["title"],
        scope=data.get("scope", "personal"),
        tiles=tiles,
        theme=theme,
        created_at=data.get("created_at", ""),
        updated_at=data.get("updated_at", ""),
    )


# ─── DashboardTemplate ────────────────────────────────────────────────────────

def save_template(t: DashboardTemplate, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = asdict(t)
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")


def load_template(path: Path) -> DashboardTemplate:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    tiles = [_tile_from_dict(t) for t in data.get("tiles", [])]
    theme = _theme_from_dict(data.get("theme"))
    return DashboardTemplate(
        id=data["id"],
        title=data["title"],
        description=data.get("description", ""),
        tiles=tiles,
        theme=theme,
    )

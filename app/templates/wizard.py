"""Wizard de création guidée de templates de dashboard."""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from app.dashboards.models import DashboardTemplate, DashboardTheme, Tile, save_template
from app.semantic.model import load_model

WIZARD_SESSIONS_PATH = Path("data/wizard_sessions.jsonl")
TEMPLATES_DIR = Path("data/dashboards/templates")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class WizardSession:
    session_id: str
    step: Literal["metrics", "dimensions", "preview", "done"]
    selected_metrics: list[str] = field(default_factory=list)
    selected_dimensions: list[str] = field(default_factory=list)
    template_name: str = ""
    generated_tiles: list[dict] = field(default_factory=list)
    created_at: str = ""


def _load_sessions(sessions_path: Path) -> dict[str, WizardSession]:
    sessions: dict[str, WizardSession] = {}
    if not sessions_path.exists():
        return sessions
    for line in sessions_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
            sessions[d["session_id"]] = WizardSession(**d)
        except Exception:
            continue
    return sessions


def _write_sessions(sessions: dict[str, WizardSession], sessions_path: Path) -> None:
    sessions_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(asdict(s)) for s in sessions.values()]
    sessions_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def new_session(sessions_path: Path = WIZARD_SESSIONS_PATH) -> WizardSession:
    session = WizardSession(
        session_id=str(uuid.uuid4()),
        step="metrics",
        created_at=_now(),
    )
    sessions = _load_sessions(sessions_path)
    sessions[session.session_id] = session
    _write_sessions(sessions, sessions_path)
    return session


def get_session(session_id: str, sessions_path: Path = WIZARD_SESSIONS_PATH) -> WizardSession | None:
    return _load_sessions(sessions_path).get(session_id)


def save_session(session: WizardSession, sessions_path: Path = WIZARD_SESSIONS_PATH) -> None:
    sessions = _load_sessions(sessions_path)
    sessions[session.session_id] = session
    _write_sessions(sessions, sessions_path)


def list_available_metrics(model_path: str = "semantic/model.yaml") -> list[dict]:
    model = load_model(model_path)
    return [
        {"name": m.name, "description": m.description, "aliases": m.aliases}
        for m in model.metrics
    ]


def list_available_dimensions(model_path: str = "semantic/model.yaml") -> list[dict]:
    model = load_model(model_path)
    dims = []
    for table in model.tables:
        for col in table.columns:
            if col.type.lower() in ("varchar", "text", "date", "timestamp", "boolean"):
                dims.append({
                    "table": table.name,
                    "column": col.name,
                    "description": col.description,
                    "key": f"{table.name}.{col.name}",
                })
    return dims


def step_select_metrics(
    session_id: str,
    metrics: list[str],
    sessions_path: Path = WIZARD_SESSIONS_PATH,
    model_path: str = "semantic/model.yaml",
) -> WizardSession:
    session = get_session(session_id, sessions_path)
    if session is None:
        raise ValueError(f"Session inconnue : {session_id!r}")
    available = {m["name"] for m in list_available_metrics(model_path)}
    unknown = [m for m in metrics if m not in available]
    if unknown:
        raise ValueError(f"Métriques inconnues : {unknown}")
    if not metrics:
        raise ValueError("Sélectionner au moins une métrique.")
    session.selected_metrics = list(metrics)
    session.step = "dimensions"
    save_session(session, sessions_path)
    return session


def step_select_dimensions(
    session_id: str,
    dimensions: list[str],
    sessions_path: Path = WIZARD_SESSIONS_PATH,
    model_path: str = "semantic/model.yaml",
) -> WizardSession:
    session = get_session(session_id, sessions_path)
    if session is None:
        raise ValueError(f"Session inconnue : {session_id!r}")
    available_keys = {d["key"] for d in list_available_dimensions(model_path)}
    unknown = [d for d in dimensions if d not in available_keys]
    if unknown:
        raise ValueError(f"Dimensions inconnues : {unknown}")
    if not dimensions:
        raise ValueError("Sélectionner au moins une dimension.")
    session.selected_dimensions = list(dimensions)
    session.step = "preview"
    save_session(session, sessions_path)
    return session


def step_generate_preview(
    session_id: str,
    template_name: str,
    sessions_path: Path = WIZARD_SESSIONS_PATH,
    model_path: str = "semantic/model.yaml",
) -> WizardSession:
    session = get_session(session_id, sessions_path)
    if session is None:
        raise ValueError(f"Session inconnue : {session_id!r}")
    if session.step != "preview":
        raise ValueError("Étape incorrecte : passer d'abord par 'metrics' puis 'dimensions'.")

    model = load_model(model_path)
    metric_map = {m.name: m for m in model.metrics}

    tiles: list[dict] = []
    tile_idx = 0

    for metric_name in session.selected_metrics:
        metric = metric_map.get(metric_name)
        if metric is None:
            continue
        main_table = metric.tables[0] if metric.tables else "ventes_detail"

        # KPI global
        tiles.append({
            "id": f"t{tile_idx}",
            "type": "kpi",
            "title": metric_name,
            "sql_pinned": f"SELECT {metric.sql} AS valeur FROM {main_table}",
        })
        tile_idx += 1

        # Bar par dimension
        for dim_key in session.selected_dimensions:
            table_name, col_name = dim_key.split(".", 1)
            tiles.append({
                "id": f"t{tile_idx}",
                "type": "bar",
                "title": f"{metric_name} par {col_name}",
                "sql_pinned": (
                    f"SELECT {dim_key}, {metric.sql} AS valeur "
                    f"FROM {main_table} "
                    f"LEFT JOIN {table_name} ON {main_table}.id_{table_name[:-1] if table_name.endswith('s') else table_name} = {table_name}.id_{table_name[:-1] if table_name.endswith('s') else table_name} "
                    f"GROUP BY {dim_key} ORDER BY valeur DESC LIMIT 20"
                    if table_name != main_table
                    else
                    f"SELECT {col_name}, {metric.sql} AS valeur "
                    f"FROM {main_table} "
                    f"GROUP BY {col_name} ORDER BY valeur DESC LIMIT 20"
                ),
            })
            tile_idx += 1

    session.template_name = template_name.strip() or "Nouveau template"
    session.generated_tiles = tiles
    save_session(session, sessions_path)
    return session


def step_confirm(
    session_id: str,
    sessions_path: Path = WIZARD_SESSIONS_PATH,
    templates_dir: Path = TEMPLATES_DIR,
) -> dict:
    session = get_session(session_id, sessions_path)
    if session is None:
        raise ValueError(f"Session inconnue : {session_id!r}")
    if session.step != "preview" or not session.generated_tiles:
        raise ValueError("Étape incorrecte : lancer d'abord step_generate_preview.")

    template_id = str(uuid.uuid4())
    tiles = [
        Tile(
            id=t["id"],
            type=t["type"],
            title=t["title"],
            sql_pinned=t.get("sql_pinned"),
        )
        for t in session.generated_tiles
    ]
    template = DashboardTemplate(
        id=template_id,
        title=session.template_name,
        description=f"Généré par le wizard — métriques : {', '.join(session.selected_metrics)}",
        tiles=tiles,
        theme=DashboardTheme(),
    )
    save_template(template, templates_dir / f"{template_id}.yaml")

    session.step = "done"
    save_session(session, sessions_path)

    return {"template_id": template_id, "tile_count": len(tiles)}

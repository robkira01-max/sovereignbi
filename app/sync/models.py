"""Modèles de données pour la synchronisation automatique."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

SYNC_DIR = Path("data/sync")
SCHEDULES_FILE = SYNC_DIR / "schedules.jsonl"
RUNS_FILE = SYNC_DIR / "runs.jsonl"

SUPPORTED_CONNECTORS = {"postgres", "mysql", "mssql", "snowflake", "bigquery", "mongodb"}


@dataclass
class SyncSchedule:
    schedule_id: str
    connector_type: str
    name: str
    host: str
    port: int
    database: str
    username: str
    password_enc: str
    query_or_table: str
    target_table: str
    cron_expr: str
    enabled: bool = True
    last_run_at: Optional[str] = None
    last_run_status: Optional[str] = None
    last_run_rows: Optional[int] = None
    last_error: Optional[str] = None
    consecutive_failures: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(tz=timezone.utc).isoformat())


@dataclass
class SyncRun:
    run_id: str
    schedule_id: str
    started_at: str
    finished_at: Optional[str]
    status: str
    rows_synced: Optional[int]
    error_message: Optional[str]
    duration_seconds: Optional[float]


# ── persistence helpers ──────────────────────────────────────────────────────

def _ensure_dir() -> None:
    SYNC_DIR.mkdir(parents=True, exist_ok=True)


def save_schedule(s: SyncSchedule) -> None:
    _ensure_dir()
    schedules = {sc.schedule_id: sc for sc in load_schedules()}
    schedules[s.schedule_id] = s
    SCHEDULES_FILE.write_text(
        "\n".join(json.dumps(asdict(sc)) for sc in schedules.values()) + "\n",
        encoding="utf-8",
    )


def load_schedules() -> list[SyncSchedule]:
    _ensure_dir()
    if not SCHEDULES_FILE.exists():
        return []
    out = []
    for line in SCHEDULES_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(SyncSchedule(**json.loads(line)))
            except Exception:
                pass
    return out


def get_schedule(schedule_id: str) -> Optional[SyncSchedule]:
    return next((s for s in load_schedules() if s.schedule_id == schedule_id), None)


def delete_schedule(schedule_id: str) -> bool:
    schedules = [s for s in load_schedules() if s.schedule_id != schedule_id]
    original = load_schedules()
    if len(schedules) == len(original):
        return False
    _ensure_dir()
    SCHEDULES_FILE.write_text(
        "\n".join(json.dumps(asdict(s)) for s in schedules) + ("\n" if schedules else ""),
        encoding="utf-8",
    )
    return True


def save_run(r: SyncRun) -> None:
    _ensure_dir()
    with open(RUNS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(r)) + "\n")


def load_runs(schedule_id: str) -> list[SyncRun]:
    _ensure_dir()
    if not RUNS_FILE.exists():
        return []
    out = []
    for line in RUNS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                r = SyncRun(**json.loads(line))
                if r.schedule_id == schedule_id:
                    out.append(r)
            except Exception:
                pass
    return out

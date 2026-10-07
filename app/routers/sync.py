"""Routes de synchronisation automatique des bases de données."""
from __future__ import annotations

from dataclasses import asdict
from typing import Any, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, field_validator

from app.security.rbac import RequireRole
from app.sync.credential_vault import encrypt_credential
from app.sync.models import (
    SUPPORTED_CONNECTORS,
    SyncSchedule,
    delete_schedule,
    get_schedule,
    load_runs,
    load_schedules,
    save_schedule,
)

router = APIRouter(prefix="/sync", tags=["sync"])

_VIEWER = RequireRole("viewer")
_EDITOR = RequireRole("editor")
_ADMIN = RequireRole("admin")


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class SyncScheduleCreate(BaseModel):
    connector_type: str
    name: str
    host: str
    port: int
    database: str
    username: str
    password: str
    query_or_table: str
    target_table: str
    cron_expr: str

    @field_validator("connector_type")
    @classmethod
    def validate_connector(cls, v: str) -> str:
        if v not in SUPPORTED_CONNECTORS:
            raise ValueError(f"connector_type doit être dans {sorted(SUPPORTED_CONNECTORS)}")
        return v

    @field_validator("query_or_table")
    @classmethod
    def no_multi_statement(cls, v: str) -> str:
        stripped = v.strip().rstrip(";")
        if ";" in stripped:
            raise ValueError("Les requêtes multi-instructions ne sont pas autorisées.")
        return v


def _mask(s: SyncSchedule) -> dict[str, Any]:
    d = asdict(s)
    d["password_enc"] = "***"
    return d


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/schedules", status_code=201)
def create_schedule(body: SyncScheduleCreate, _: str = Depends(_EDITOR)):
    schedule = SyncSchedule(
        schedule_id=str(uuid4()),
        connector_type=body.connector_type,
        name=body.name,
        host=body.host,
        port=body.port,
        database=body.database,
        username=body.username,
        password_enc=encrypt_credential(body.password),
        query_or_table=body.query_or_table,
        target_table=body.target_table,
        cron_expr=body.cron_expr,
    )
    save_schedule(schedule)
    return _mask(schedule)


@router.get("/schedules")
def list_schedules(_: str = Depends(_VIEWER)):
    return [_mask(s) for s in load_schedules()]


@router.get("/schedules/{schedule_id}")
def get_schedule_route(schedule_id: str, _: str = Depends(_VIEWER)):
    s = get_schedule(schedule_id)
    if s is None:
        raise HTTPException(404, "Planification introuvable.")
    return _mask(s)


@router.patch("/schedules/{schedule_id}/toggle")
def toggle_schedule(schedule_id: str, _: str = Depends(_EDITOR)):
    s = get_schedule(schedule_id)
    if s is None:
        raise HTTPException(404, "Planification introuvable.")
    s.enabled = not s.enabled
    s.consecutive_failures = 0
    save_schedule(s)
    return _mask(s)


@router.delete("/schedules/{schedule_id}", status_code=204)
def remove_schedule(schedule_id: str, _: str = Depends(_ADMIN)):
    if not delete_schedule(schedule_id):
        raise HTTPException(404, "Planification introuvable.")


@router.post("/schedules/{schedule_id}/run")
def run_schedule_now(schedule_id: str, request: Request, _: str = Depends(_EDITOR)):
    s = get_schedule(schedule_id)
    if s is None:
        raise HTTPException(404, "Planification introuvable.")
    store = request.app.state.store if hasattr(request.app.state, "store") else None
    from app.sync.sync_engine import run_sync
    from app.sync.credential_vault import decrypt_credential
    import pandas as pd

    def _mock_connector(schedule: SyncSchedule, password: str):
        return pd.DataFrame({"col": [1, 2, 3]})

    connector = _mock_connector if store is None else None
    run = run_sync(s, store, connector_factory=connector)
    from dataclasses import asdict as dc_asdict
    return dc_asdict(run)


@router.get("/schedules/{schedule_id}/history")
def schedule_history(schedule_id: str, _: str = Depends(_VIEWER)):
    s = get_schedule(schedule_id)
    if s is None:
        raise HTTPException(404, "Planification introuvable.")
    from dataclasses import asdict as dc_asdict
    return [dc_asdict(r) for r in load_runs(schedule_id)]


@router.get("/scheduler/status")
def scheduler_status(request: Request, _: str = Depends(_VIEWER)):
    scheduler = getattr(request.app.state, "scheduler", None)
    if scheduler is None:
        return {"running": False, "jobs": 0}
    return {
        "running": scheduler._running,
        "jobs": scheduler.job_count(),
    }

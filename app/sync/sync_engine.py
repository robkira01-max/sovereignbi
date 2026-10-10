"""Moteur de synchronisation — exécute une SyncSchedule et retourne un SyncRun."""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Callable, Optional
from uuid import uuid4

from app.sync.credential_vault import decrypt_credential
from app.sync.models import SyncRun, SyncSchedule, save_run, save_schedule

_CIRCUIT_BREAKER_THRESHOLD = 3


def run_sync(
    schedule: SyncSchedule,
    store: Any,
    connector_factory: Optional[Callable] = None,
) -> SyncRun:
    """Exécuter une synchronisation.

    connector_factory(schedule, password) → pandas DataFrame ou None (mock/tests).
    Si None : tente de charger via les connecteurs réels.
    """
    started_at = datetime.now(tz=timezone.utc).isoformat()
    t0 = time.perf_counter()
    run_id = str(uuid4())

    def _fail(msg: str) -> SyncRun:
        duration = round(time.perf_counter() - t0, 3)
        schedule.last_run_at = started_at
        schedule.last_run_status = "error"
        schedule.last_error = msg
        schedule.consecutive_failures = (schedule.consecutive_failures or 0) + 1
        if schedule.consecutive_failures >= _CIRCUIT_BREAKER_THRESHOLD:
            schedule.enabled = False
        save_schedule(schedule)
        run = SyncRun(
            run_id=run_id,
            schedule_id=schedule.schedule_id,
            started_at=started_at,
            finished_at=datetime.now(tz=timezone.utc).isoformat(),
            status="error",
            rows_synced=None,
            error_message=msg,
            duration_seconds=duration,
        )
        save_run(run)
        return run

    try:
        password = decrypt_credential(schedule.password_enc)
    except Exception as exc:
        return _fail(f"Impossible de déchiffrer le mot de passe : {exc}")

    try:
        if connector_factory is not None:
            df = connector_factory(schedule, password)
        else:
            df = _real_fetch(schedule, password)
    except Exception as exc:
        return _fail(str(exc))

    if df is None:
        return _fail("Le connecteur n'a retourné aucune donnée.")

    try:
        import duckdb
        from app.data.duckdb_store import _safe_name
        safe_table = _safe_name(schedule.target_table)
        store.con.execute(f'DROP TABLE IF EXISTS "{safe_table}"')
        store.con.execute(
            f'CREATE TABLE "{safe_table}" AS SELECT * FROM df'
        )
        rows = len(df)
    except Exception as exc:
        return _fail(f"Impossible de charger les données dans DuckDB : {exc}")

    duration = round(time.perf_counter() - t0, 3)
    schedule.last_run_at = started_at
    schedule.last_run_status = "success"
    schedule.last_run_rows = rows
    schedule.last_error = None
    schedule.consecutive_failures = 0
    save_schedule(schedule)

    run = SyncRun(
        run_id=run_id,
        schedule_id=schedule.schedule_id,
        started_at=started_at,
        finished_at=datetime.now(tz=timezone.utc).isoformat(),
        status="success",
        rows_synced=rows,
        error_message=None,
        duration_seconds=duration,
    )
    save_run(run)
    return run


def _real_fetch(schedule: SyncSchedule, password: str):
    """Charger les données via les connecteurs existants."""
    import pandas as pd

    ct = schedule.connector_type
    q = schedule.query_or_table
    if not q.strip().upper().startswith("SELECT"):
        q = f'SELECT * FROM "{q}"'

    if ct == "postgres":
        import psycopg2
        conn = psycopg2.connect(
            host=schedule.host, port=schedule.port, dbname=schedule.database,
            user=schedule.username, password=password,
        )
        df = pd.read_sql(q, conn)
        conn.close()
        return df

    if ct == "mysql":
        import pymysql
        conn = pymysql.connect(
            host=schedule.host, port=schedule.port, database=schedule.database,
            user=schedule.username, password=password,
        )
        df = pd.read_sql(q, conn)
        conn.close()
        return df

    if ct == "mssql":
        import pymssql
        conn = pymssql.connect(
            server=schedule.host, port=str(schedule.port), database=schedule.database,
            user=schedule.username, password=password,
        )
        df = pd.read_sql(q, conn)
        conn.close()
        return df

    raise ValueError(f"Connecteur '{ct}' non supporté pour la synchro directe.")

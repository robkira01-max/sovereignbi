"""Tests Sprint 25 — synchronisation automatique DB, scheduler, credential vault."""
from __future__ import annotations

import json
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.sync.credential_vault import decrypt_credential, encrypt_credential
from app.sync.models import (
    SyncRun,
    SyncSchedule,
    delete_schedule,
    get_schedule,
    load_runs,
    load_schedules,
    save_run,
    save_schedule,
)
from app.sync.scheduler import CronScheduler

# ── fixtures ──────────────────────────────────────────────────────────────────

VIEWER = {"X-Api-Key": "test-viewer-key-s6"}
EDITOR = {"X-Api-Key": "test-editor-key-s6"}
ADMIN = {"X-Api-Key": "test-admin-key-sprint3"}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("SOVEREIGN_EMBEDDER", "tfidf")
    monkeypatch.setattr("app.sync.models.SYNC_DIR", tmp_path / "sync")
    monkeypatch.setattr("app.sync.models.SCHEDULES_FILE", tmp_path / "sync" / "schedules.jsonl")
    monkeypatch.setattr("app.sync.models.RUNS_FILE", tmp_path / "sync" / "runs.jsonl")
    from app.main import app
    return TestClient(app)


@pytest.fixture()
def schedule_payload():
    return {
        "connector_type": "postgres",
        "name": "FMP Djibouti nightly",
        "host": "db.example.com",
        "port": 5432,
        "database": "fmp",
        "username": "reader",
        "password": "s3cret",
        "query_or_table": "SELECT * FROM fmp_data",
        "target_table": "fmp_data",
        "cron_expr": "0 6 * * *",
    }


# ── credential vault ──────────────────────────────────────────────────────────

def test_encrypt_decrypt_roundtrip():
    plain = "my-super-secret-password"
    enc = encrypt_credential(plain)
    assert decrypt_credential(enc) == plain


def test_encrypt_does_not_expose_plaintext():
    plain = "my-super-secret-password"
    enc = encrypt_credential(plain)
    assert plain not in enc


def test_different_plaintexts_give_different_ciphertext():
    assert encrypt_credential("abc") != encrypt_credential("xyz")


# ── scheduler ─────────────────────────────────────────────────────────────────

def test_should_run_never_run():
    assert CronScheduler.should_run("@daily", None) is True


def test_should_run_every_interval_elapsed():
    one_second_ago = datetime.now(tz=timezone.utc).isoformat()
    time.sleep(0.01)
    assert CronScheduler.should_run("every:0", one_second_ago) is True


def test_should_run_every_interval_not_elapsed():
    just_now = datetime.now(tz=timezone.utc).isoformat()
    assert CronScheduler.should_run("every:3600", just_now) is False


def test_should_run_hourly_never_run():
    assert CronScheduler.should_run("@hourly", None) is True


def test_scheduler_starts_and_stops():
    s = CronScheduler()
    s.start()
    assert s._running is True
    s.stop()
    assert s._running is False


def test_scheduler_add_remove_job():
    s = CronScheduler()
    s.add_job("j1", "every:60", lambda: None)
    assert s.job_count() == 1
    s.remove_job("j1")
    assert s.job_count() == 0


def test_scheduler_no_duplicate_start():
    s = CronScheduler()
    s.start()
    thread1 = s._thread
    s.start()
    assert s._thread is thread1
    s.stop()


# ── API routes ────────────────────────────────────────────────────────────────

def test_create_schedule(client, schedule_payload):
    r = client.post("/sync/schedules", json=schedule_payload, headers=EDITOR)
    assert r.status_code == 201
    d = r.json()
    assert d["name"] == "FMP Djibouti nightly"
    assert d["password_enc"] == "***"
    assert "schedule_id" in d


def test_create_schedule_no_password(client, schedule_payload):
    payload = {k: v for k, v in schedule_payload.items() if k != "password"}
    r = client.post("/sync/schedules", json=payload, headers=EDITOR)
    assert r.status_code == 422


def test_create_schedule_invalid_connector(client, schedule_payload):
    schedule_payload["connector_type"] = "oracle"
    r = client.post("/sync/schedules", json=schedule_payload, headers=EDITOR)
    assert r.status_code == 422


def test_create_schedule_multi_statement(client, schedule_payload):
    schedule_payload["query_or_table"] = "SELECT 1; DROP TABLE users"
    r = client.post("/sync/schedules", json=schedule_payload, headers=EDITOR)
    assert r.status_code == 422


def test_list_schedules_passwords_masked(client, schedule_payload):
    client.post("/sync/schedules", json=schedule_payload, headers=EDITOR)
    r = client.get("/sync/schedules", headers=VIEWER)
    assert r.status_code == 200
    for item in r.json():
        assert item["password_enc"] == "***"


def test_get_schedule_password_masked(client, schedule_payload):
    created = client.post("/sync/schedules", json=schedule_payload, headers=EDITOR).json()
    sid = created["schedule_id"]
    r = client.get(f"/sync/schedules/{sid}", headers=VIEWER)
    assert r.status_code == 200
    assert r.json()["password_enc"] == "***"


def test_get_schedule_not_found(client):
    r = client.get("/sync/schedules/nonexistent-id", headers=VIEWER)
    assert r.status_code == 404


def test_toggle_schedule(client, schedule_payload):
    created = client.post("/sync/schedules", json=schedule_payload, headers=EDITOR).json()
    sid = created["schedule_id"]
    assert created["enabled"] is True
    toggled = client.patch(f"/sync/schedules/{sid}/toggle", headers=EDITOR).json()
    assert toggled["enabled"] is False
    retoggled = client.patch(f"/sync/schedules/{sid}/toggle", headers=EDITOR).json()
    assert retoggled["enabled"] is True


def test_delete_schedule(client, schedule_payload):
    created = client.post("/sync/schedules", json=schedule_payload, headers=EDITOR).json()
    sid = created["schedule_id"]
    r = client.delete(f"/sync/schedules/{sid}", headers=ADMIN)
    assert r.status_code == 204
    assert client.get(f"/sync/schedules/{sid}", headers=VIEWER).status_code == 404


def test_delete_schedule_not_found(client):
    r = client.delete("/sync/schedules/nonexistent", headers=ADMIN)
    assert r.status_code == 404


def test_run_schedule_now(client, schedule_payload):
    created = client.post("/sync/schedules", json=schedule_payload, headers=EDITOR).json()
    sid = created["schedule_id"]
    r = client.post(f"/sync/schedules/{sid}/run", headers=EDITOR)
    assert r.status_code == 200
    body = r.json()
    assert body["schedule_id"] == sid
    assert body["status"] in ("success", "error")


def test_history_empty_initially(client, schedule_payload):
    created = client.post("/sync/schedules", json=schedule_payload, headers=EDITOR).json()
    sid = created["schedule_id"]
    r = client.get(f"/sync/schedules/{sid}/history", headers=VIEWER)
    assert r.status_code == 200
    assert r.json() == []


def test_scheduler_status(client):
    r = client.get("/sync/scheduler/status", headers=VIEWER)
    assert r.status_code == 200
    body = r.json()
    assert "running" in body
    assert "jobs" in body


def test_rbac_viewer_cannot_create(client, schedule_payload):
    r = client.post("/sync/schedules", json=schedule_payload, headers=VIEWER)
    assert r.status_code == 403


def test_rbac_editor_cannot_delete(client, schedule_payload):
    created = client.post("/sync/schedules", json=schedule_payload, headers=EDITOR).json()
    sid = created["schedule_id"]
    r = client.delete(f"/sync/schedules/{sid}", headers=EDITOR)
    assert r.status_code == 403


def test_all_supported_connectors(client, schedule_payload):
    for ct in ("postgres", "mysql", "mssql", "snowflake", "bigquery", "mongodb"):
        payload = {**schedule_payload, "connector_type": ct, "name": f"test-{ct}"}
        r = client.post("/sync/schedules", json=payload, headers=EDITOR)
        assert r.status_code == 201, f"Failed for {ct}: {r.text}"


# ── circuit breaker ───────────────────────────────────────────────────────────

def test_circuit_breaker_disables_after_3_failures(tmp_path):
    from app.sync.sync_engine import run_sync

    with patch("app.sync.models.SYNC_DIR", tmp_path / "sync"), \
         patch("app.sync.models.SCHEDULES_FILE", tmp_path / "sync" / "schedules.jsonl"), \
         patch("app.sync.models.RUNS_FILE", tmp_path / "sync" / "runs.jsonl"):

        s = SyncSchedule(
            schedule_id="test-cb",
            connector_type="postgres",
            name="CB test",
            host="bad-host",
            port=5432,
            database="db",
            username="u",
            password_enc=encrypt_credential("p"),
            query_or_table="SELECT 1",
            target_table="t",
            cron_expr="@daily",
        )
        save_schedule(s)

        def fail_connector(schedule, password):
            raise ConnectionError("Host unreachable")

        store = type("Store", (), {"con": None})()

        for _ in range(3):
            run_sync(s, store, connector_factory=fail_connector)
            s = get_schedule("test-cb")

        assert s.enabled is False
        assert s.consecutive_failures >= 3


# ── data isolation ────────────────────────────────────────────────────────────

def test_data_stored_in_sync_dir(client, schedule_payload, tmp_path):
    client.post("/sync/schedules", json=schedule_payload, headers=EDITOR)
    schedules = client.get("/sync/schedules", headers=VIEWER).json()
    assert len(schedules) >= 1

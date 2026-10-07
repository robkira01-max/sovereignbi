"""Tests onboarding guidé + sandbox Sprint 19."""
import pytest
from fastapi.testclient import TestClient

from app.main import app, store
from app.onboarding.guide import (
    ONBOARDING_STEPS,
    complete_step,
    create_session,
    get_progress,
    get_session,
)
from app.onboarding.sandbox import SANDBOX_TABLES, load_sandbox, reset_sandbox, sandbox_questions

VIEWER = {"X-Api-Key": "test-viewer-key-s6"}
EDITOR = {"X-Api-Key": "test-editor-key-s6"}
ADMIN = {"X-Api-Key": "test-admin-key-sprint3"}


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset():
    store.tables.clear()
    yield


# --- Guide unit tests ---

def test_create_session(tmp_path):
    p = tmp_path / "ob.jsonl"
    s = create_session("u1", path=p)
    assert s.session_id
    assert s.user_id == "u1"
    assert len(s.steps) == len(ONBOARDING_STEPS)
    assert all(st.status == "pending" for st in s.steps)


def test_get_session(tmp_path):
    p = tmp_path / "ob.jsonl"
    s = create_session("u1", path=p)
    found = get_session(s.session_id, path=p)
    assert found is not None
    assert found.session_id == s.session_id


def test_complete_step(tmp_path):
    p = tmp_path / "ob.jsonl"
    s = create_session("u1", path=p)
    first_step = ONBOARDING_STEPS[0]["step_id"]
    updated = complete_step(s.session_id, first_step, path=p)
    matching = [st for st in updated.steps if st.step_id == first_step]
    assert matching[0].status == "completed"
    assert matching[0].completed_at is not None


def test_session_completed_when_all_steps_done(tmp_path):
    p = tmp_path / "ob.jsonl"
    s = create_session("u1", path=p)
    for step in ONBOARDING_STEPS:
        complete_step(s.session_id, step["step_id"], path=p)
    progress = get_progress(s.session_id, path=p)
    assert progress["completed"] is True
    assert progress["progress_pct"] == 100


def test_get_progress(tmp_path):
    p = tmp_path / "ob.jsonl"
    s = create_session("u1", path=p)
    first = ONBOARDING_STEPS[0]["step_id"]
    complete_step(s.session_id, first, path=p)
    prog = get_progress(s.session_id, path=p)
    assert prog["completed_steps"] == 1
    assert prog["total_steps"] == len(ONBOARDING_STEPS)
    assert prog["progress_pct"] > 0


def test_complete_step_session_not_found(tmp_path):
    p = tmp_path / "ob.jsonl"
    with pytest.raises(KeyError):
        complete_step("nonexistent", "step-upload", path=p)


# --- Sandbox unit tests ---

def test_load_sandbox():
    ds = store
    ds.tables.clear()
    tables = load_sandbox(ds)
    assert set(tables) == set(SANDBOX_TABLES.keys())
    for t in tables:
        assert t in ds.tables


def test_reset_sandbox():
    load_sandbox(store)
    store.tables.add("extra_table")
    tables = reset_sandbox(store)
    assert "extra_table" not in store.tables
    assert set(tables) == set(SANDBOX_TABLES.keys())


def test_sandbox_questions_format():
    questions = sandbox_questions()
    assert len(questions) >= 3
    for q in questions:
        assert "question" in q
        assert "table" in q


# --- Route tests ---

def test_list_steps_route(client):
    r = client.get("/onboarding/steps", headers=VIEWER)
    assert r.status_code == 200
    steps = r.json()["steps"]
    assert len(steps) == len(ONBOARDING_STEPS)
    assert steps[0]["step_id"] == "step-upload"


def test_start_session_route(client):
    r = client.post("/onboarding/sessions", json={"user_id": "alice"}, headers=VIEWER)
    assert r.status_code == 200
    assert r.json()["user_id"] == "alice"


def test_get_session_progress_route(client):
    create_r = client.post("/onboarding/sessions", json={"user_id": "bob"}, headers=VIEWER)
    session_id = create_r.json()["session_id"]

    progress_r = client.get(f"/onboarding/sessions/{session_id}", headers=VIEWER)
    assert progress_r.status_code == 200
    prog = progress_r.json()
    assert prog["total_steps"] == len(ONBOARDING_STEPS)
    assert prog["completed_steps"] == 0


def test_complete_step_route(client):
    create_r = client.post("/onboarding/sessions", json={"user_id": "carol"}, headers=VIEWER)
    session_id = create_r.json()["session_id"]

    comp = client.post(
        f"/onboarding/sessions/{session_id}/complete",
        json={"step_id": "step-upload"},
        headers=VIEWER,
    )
    assert comp.status_code == 200
    assert comp.json()["completed_steps"] == 1


def test_load_sandbox_route(client):
    r = client.post("/onboarding/sandbox/load", headers=EDITOR)
    assert r.status_code == 200
    data = r.json()
    assert "ventes" in data["tables"]
    assert isinstance(data["questions"], list)


def test_reset_sandbox_route(client):
    client.post("/onboarding/sandbox/load", headers=EDITOR)
    r = client.post("/onboarding/sandbox/reset", headers=ADMIN)
    assert r.status_code == 200
    assert r.json()["reset"] is True


def test_sandbox_questions_route(client):
    r = client.get("/onboarding/sandbox/questions", headers=VIEWER)
    assert r.status_code == 200
    assert len(r.json()["questions"]) >= 3


def test_session_not_found_route(client):
    r = client.get("/onboarding/sessions/nonexistent", headers=VIEWER)
    assert r.status_code == 404

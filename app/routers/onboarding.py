"""Routes onboarding guidé + démo sandbox."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.onboarding.guide import (
    ONBOARDING_STEPS,
    complete_step,
    create_session,
    get_progress,
    get_session,
)
from app.onboarding.sandbox import load_sandbox, reset_sandbox, sandbox_questions
from app.security.rbac import RequireRole

router = APIRouter(prefix="/onboarding", tags=["onboarding"])

_VIEWER = RequireRole("viewer")
_EDITOR = RequireRole("editor")
_ADMIN = RequireRole("admin")


class SessionCreate(BaseModel):
    user_id: str


class StepComplete(BaseModel):
    step_id: str


@router.get("/steps")
def list_steps(_: str = Depends(_VIEWER)):
    return {"steps": ONBOARDING_STEPS}


@router.post("/sessions")
def start_session(body: SessionCreate, _: str = Depends(_VIEWER)):
    session = create_session(body.user_id)
    return {"session_id": session.session_id, "user_id": session.user_id}


@router.get("/sessions/{session_id}")
def get_session_progress(session_id: str, _: str = Depends(_VIEWER)):
    try:
        return get_progress(session_id)
    except KeyError:
        raise HTTPException(404, "Session introuvable")


@router.post("/sessions/{session_id}/complete")
def mark_step_complete(session_id: str, body: StepComplete, _: str = Depends(_VIEWER)):
    try:
        session = complete_step(session_id, body.step_id)
        return get_progress(session_id)
    except KeyError:
        raise HTTPException(404, "Session ou étape introuvable")


@router.post("/sandbox/load")
def load_sandbox_data(request: Request, _: str = Depends(_EDITOR)):
    store = request.app.state.store
    tables = load_sandbox(store)
    return {"tables": tables, "questions": sandbox_questions()}


@router.post("/sandbox/reset")
def reset_sandbox_data(request: Request, _: str = Depends(_ADMIN)):
    store = request.app.state.store
    tables = reset_sandbox(store)
    request.app.state.query_cache.invalidate()
    return {"tables": tables, "reset": True}


@router.get("/sandbox/questions")
def get_sandbox_questions(_: str = Depends(_VIEWER)):
    return {"questions": sandbox_questions()}

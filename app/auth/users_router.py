"""Account management — admin-only user CRUD plus self-service password change."""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from typing import Annotated, Literal

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Path, Request, Response
from pydantic import BaseModel, Field

from app.api.middleware import RateLimitMiddleware, bucket_key
from app.feedback import record_audit
from app.security.audit import _DEFAULT_KEYS
from app.security.rbac import RequireRole

from . import security as sec
from .router import _throttle

log = structlog.get_logger()


def _no_store(response: Response) -> None:
    # Responses carry e-mail addresses and roles: never cache them.
    response.headers["Cache-Control"] = "no-store"


router = APIRouter(prefix="/auth", tags=["auth"], dependencies=[Depends(_no_store)])

Role = Literal["viewer", "editor", "admin"]
UserId = Annotated[int, Path(ge=1, le=2**63 - 1)]  # sqlite INTEGER range; larger values would 500
_ADMIN = RequireRole("admin")


class UserOut(BaseModel):
    id: int
    email: str
    role: Role
    is_active: bool
    created_at: str | None = None


class UserCreate(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=256)
    role: Role = "viewer"


class UserUpdate(BaseModel):
    role: Role | None = None
    is_active: bool | None = None


class PasswordReset(BaseModel):
    password: str = Field(max_length=256)


class PasswordChange(BaseModel):
    current_password: str = Field(max_length=256)
    new_password: str = Field(max_length=256)


def _actor(request: Request, _role: str = Depends(_ADMIN)) -> str:
    """Who is acting, for the audit trail. Mirrors RequireRole: X-Api-Key wins over Bearer."""
    api_key = request.headers.get("x-api-key", "")
    if api_key:
        # An admin API key can mint permanent accounts that outlive its rotation, so a
        # placeholder key from .env.example must never be honoured in production.
        if os.environ.get("APP_ENV", "development").lower() == "production" and api_key in _DEFAULT_KEYS:
            raise HTTPException(403, "Clé API par défaut refusée en production.")
        return "api_key"
    auth = request.headers.get("authorization", "")
    user = sec.verify_session(auth[7:]) if auth.startswith("Bearer ") else None
    return f"user:{user['id']}" if user else "session:revoked"


def _audit(action: str, actor: str, **details) -> None:
    # Best effort: the change is already committed, so a full disk must not turn a
    # successful operation into a reported failure. Never put passwords/hashes in `details`.
    try:
        record_audit(action, {"actor": actor, **details})
    except OSError:
        log.error("audit_write_failed", action=action)


@contextmanager
def _db_guard():
    """Map a locked/unavailable auth database to 503 and validation errors to 422."""
    try:
        yield
    except sqlite3.OperationalError as e:
        log.error("auth_db_unavailable", error=str(e))
        raise HTTPException(503, "Base d'authentification occupée, réessayez.") from e
    except (sec.UserExistsError, sec.LastAdminError):
        raise  # ValueError subclasses that callers map to 409, not a validation error
    except ValueError as e:
        raise HTTPException(422, str(e)) from e


@router.get("/users", response_model=list[UserOut])
def list_users(_: str = Depends(_actor)) -> list[dict]:
    with _db_guard():
        return sec.list_users()


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(body: UserCreate, actor: str = Depends(_actor)) -> dict:
    try:
        with _db_guard():
            email = sec.validate_email(body.email)
            sec.validate_password(body.password)
            user_id = sec.create_user(email, body.password, body.role)
            user = sec.get_user(user_id)
    except sec.UserExistsError as e:
        raise HTTPException(409, str(e)) from e
    _audit("user_created", actor, user_id=user_id, role=body.role)
    return user


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: UserId, body: UserUpdate, actor: str = Depends(_actor)) -> dict:
    if body.role is None and body.is_active is None:
        raise HTTPException(422, "Rien à modifier (role ou is_active requis).")
    try:
        with _db_guard():
            user = sec.update_user(user_id, role=body.role, is_active=body.is_active)
    except sec.UserNotFoundError as e:
        raise HTTPException(404, "Utilisateur introuvable.") from e
    except sec.LastAdminError as e:
        raise HTTPException(409, str(e)) from e
    _audit("user_updated", actor, user_id=user_id, role=body.role, is_active=body.is_active)
    return user


@router.put("/users/{user_id}/password", status_code=204)
def reset_password(user_id: UserId, body: PasswordReset, actor: str = Depends(_actor)) -> None:
    try:
        with _db_guard():
            sec.validate_password(body.password)
            sec.set_password(user_id, body.password)
    except sec.UserNotFoundError as e:
        raise HTTPException(404, "Utilisateur introuvable.") from e
    _audit("user_password_reset", actor, user_id=user_id)


@router.post("/password", status_code=204)
def change_password(
    body: PasswordChange,
    request: Request,
    authorization: str | None = Header(default=None),
) -> None:
    """Self-service: any logged-in web user. Other sessions of the account are revoked."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Authentification requise.")
    token = authorization[7:]
    user = sec.verify_session(token)
    if not user:
        raise HTTPException(401, "Session expirée ou invalide.")
    with _db_guard():
        sec.validate_password(body.new_password)
    # Throttle guesses of the current password (e.g. by someone holding a stolen session).
    key, client = str(user["id"]), bucket_key(RateLimitMiddleware._client_ip(request))
    if not _throttle.reserve(key, client, ns="pwchange"):
        raise HTTPException(429, "Trop de tentatives. Réessayez dans 15 minutes.")
    with _db_guard():
        changed = sec.change_own_password(user["id"], body.current_password, body.new_password, keep_token=token)
    if not changed:
        raise HTTPException(403, "Mot de passe actuel incorrect.")
    _throttle.clear(key, client, ns="pwchange")
    _audit("password_changed", f"user:{user['id']}", user_id=user["id"])

"""Auth router — POST /auth/login, POST /auth/logout, GET /auth/me."""
from __future__ import annotations

import time
from collections import defaultdict

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from .security import login_user, logout_user, verify_session

router = APIRouter(prefix="/auth", tags=["auth"])

_WINDOW = 900.0
_MAX_FAIL = 5
_hits: dict[str, list[float]] = defaultdict(list)


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    token: str
    email: str


@router.post("/login", response_model=LoginResponse)
def auth_login(body: LoginRequest) -> LoginResponse:
    now = time.monotonic()
    recent = [t for t in _hits[body.email] if now - t < _WINDOW]
    if len(recent) >= _MAX_FAIL:
        raise HTTPException(429, "Trop de tentatives. Réessayez dans 15 minutes.")
    token = login_user(body.email, body.password)
    if not token:
        _hits[body.email] = recent + [now]
        raise HTTPException(401, "Email ou mot de passe incorrect.")
    _hits[body.email] = []
    return LoginResponse(token=token, email=body.email)


@router.post("/logout", status_code=204)
def auth_logout(authorization: str | None = Header(default=None)) -> None:
    if authorization and authorization.startswith("Bearer "):
        logout_user(authorization[7:])


@router.get("/me")
def auth_me(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Non authentifié.")
    user = verify_session(authorization[7:])
    if not user:
        raise HTTPException(401, "Session expirée ou invalide.")
    return user

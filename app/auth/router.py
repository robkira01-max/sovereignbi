"""Auth router — POST /auth/login, POST /auth/logout, GET /auth/me."""
from __future__ import annotations

import threading
import time

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from app.api.middleware import RateLimitMiddleware, bucket_key

from .security import login_user, logout_user, verify_session

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginThrottle:
    """Failed-login limiter, safe under concurrent requests.

    Two counters per attempt: (email, client) is the hard lock a legitimate user hits
    after a few typos; email alone has a higher ceiling so a distributed guesser is
    still capped, while a single attacker cannot lock a known account (e.g. the admin)
    with just a handful of requests. The attempt is reserved *before* the slow bcrypt
    check so a parallel burst cannot all slip through the same check.
    """

    def __init__(self, window: float = 900.0, max_per_client: int = 5,
                 max_per_email: int = 20, max_keys: int = 10_000) -> None:
        self.window = window
        self.max_per_client = max_per_client
        self.max_per_email = max_per_email
        self.max_keys = max_keys
        self._lock = threading.Lock()
        self._attempts: dict[tuple, list[float]] = {}

    def _count(self, key: tuple, now: float) -> int:
        fresh = [t for t in self._attempts.get(key, ()) if now - t < self.window]
        if fresh:
            self._attempts[key] = fresh
        else:
            self._attempts.pop(key, None)
        return len(fresh)

    def _sweep(self, now: float) -> None:
        for k in list(self._attempts):
            self._count(k, now)

    def reserve(self, email: str, client: str) -> bool:
        now = time.monotonic()
        with self._lock:
            if len(self._attempts) > self.max_keys:
                self._sweep(now)
            by_client, by_email = ("c", email, client), ("e", email)
            if self._count(by_client, now) >= self.max_per_client:
                return False
            if self._count(by_email, now) >= self.max_per_email:
                return False
            self._attempts.setdefault(by_client, []).append(now)
            self._attempts.setdefault(by_email, []).append(now)
            return True

    def clear(self, email: str, client: str) -> None:
        with self._lock:
            self._attempts.pop(("c", email, client), None)
            self._attempts.pop(("e", email), None)

    def reset(self) -> None:
        with self._lock:
            self._attempts.clear()


_throttle = LoginThrottle()


class LoginRequest(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=256)


class LoginResponse(BaseModel):
    token: str
    email: str


@router.post("/login", response_model=LoginResponse)
def auth_login(body: LoginRequest, request: Request) -> LoginResponse:
    # users.email is COLLATE NOCASE, so the throttle key must ignore case too.
    email = body.email.strip().lower()
    client = bucket_key(RateLimitMiddleware._client_ip(request))
    if not _throttle.reserve(email, client):
        raise HTTPException(429, "Trop de tentatives. Réessayez dans 15 minutes.")
    token = login_user(body.email, body.password)
    if not token:
        raise HTTPException(401, "Email ou mot de passe incorrect.")
    _throttle.clear(email, client)
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

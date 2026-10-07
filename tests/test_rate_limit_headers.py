"""Tests pour les en-têtes X-RateLimit-* dans RateLimitMiddleware."""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=True)

_ADMIN = {"X-Api-Key": "test-admin-key-sprint3"}


def test_ratelimit_limit_header_present():
    resp = client.get("/health")
    # /health is exempt — headers may not be set; test a non-exempt endpoint
    resp = client.get("/v1/tables", headers=_ADMIN)
    assert "X-RateLimit-Limit" in resp.headers


def test_ratelimit_remaining_header_present():
    resp = client.get("/v1/tables", headers=_ADMIN)
    assert "X-RateLimit-Remaining" in resp.headers


def test_ratelimit_reset_header_present():
    resp = client.get("/v1/tables", headers=_ADMIN)
    assert "X-RateLimit-Reset" in resp.headers


def test_ratelimit_remaining_is_integer():
    resp = client.get("/v1/tables", headers=_ADMIN)
    remaining = resp.headers.get("X-RateLimit-Remaining", "")
    assert remaining.isdigit(), f"X-RateLimit-Remaining={remaining!r} is not an integer"


def test_ratelimit_reset_is_integer():
    resp = client.get("/v1/tables", headers=_ADMIN)
    reset = resp.headers.get("X-RateLimit-Reset", "")
    assert reset.isdigit(), f"X-RateLimit-Reset={reset!r} is not an integer"


def test_ratelimit_limit_matches_env():
    import os
    rpm = int(os.environ.get("SOVEREIGN_RATE_LIMIT_RPM", "60"))
    resp = client.get("/v1/tables", headers=_ADMIN)
    assert resp.headers.get("X-RateLimit-Limit") == str(rpm)

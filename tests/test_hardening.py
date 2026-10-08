"""Tests Sprint 22 — productionisation + hardening."""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.api.middleware import RateLimitMiddleware, SecurityHeadersMiddleware, _RATE_EXEMPT
from app.main import app
from app.startup import validate_env


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    return TestClient(app)


# ── Security headers ──────────────────────────────────────────────────────────

def test_security_headers_present(client):
    r = client.get("/health")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert r.headers.get("X-XSS-Protection") == "1; mode=block"
    assert r.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


def test_csp_header(client):
    r = client.get("/health")
    csp = r.headers.get("Content-Security-Policy", "")
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp


def test_hsts_header(client):
    r = client.get("/health")
    hsts = r.headers.get("Strict-Transport-Security", "")
    assert "max-age=63072000" in hsts
    assert "includeSubDomains" in hsts


def test_permissions_policy_header(client):
    r = client.get("/health")
    perms = r.headers.get("Permissions-Policy", "")
    assert "geolocation=()" in perms
    assert "camera=()" in perms


def test_x_api_version_header(client):
    r = client.get("/health")
    assert r.headers.get("X-API-Version") == "v1"


def test_x_response_time_header(client):
    r = client.get("/health")
    rt = r.headers.get("X-Response-Time", "")
    assert rt.endswith("ms")
    assert float(rt.replace("ms", "")) >= 0


# ── Rate limiting ─────────────────────────────────────────────────────────────

def test_rate_limit_exempt_paths():
    """Health/probe/metrics paths must not be rate-limited."""
    assert "/health" in _RATE_EXEMPT
    assert "/live" in _RATE_EXEMPT
    assert "/ready" in _RATE_EXEMPT
    assert "/metrics" in _RATE_EXEMPT


def test_rate_limit_allows_under_threshold():
    """Under the limit: every request should succeed."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient as TC

    mini = FastAPI()

    @mini.get("/ping")
    def ping():
        return {"ok": True}

    mini.add_middleware(RateLimitMiddleware, rpm=5)
    c = TC(mini)
    for _ in range(5):
        r = c.get("/ping")
        assert r.status_code == 200


def test_rate_limit_blocks_over_threshold():
    """Once the limit is exceeded the middleware returns 429."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient as TC

    mini = FastAPI()

    @mini.get("/ping")
    def ping():
        return {"ok": True}

    mini.add_middleware(RateLimitMiddleware, rpm=3)
    c = TC(mini)
    results = [c.get("/ping").status_code for _ in range(5)]
    assert results[:3] == [200, 200, 200]
    assert 429 in results[3:]


def test_rate_limit_429_has_retry_after():
    """429 response must carry a Retry-After header."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient as TC

    mini = FastAPI()

    @mini.get("/ping")
    def ping():
        return {"ok": True}

    mini.add_middleware(RateLimitMiddleware, rpm=1)
    c = TC(mini)
    c.get("/ping")  # consume the one allowed request
    r = c.get("/ping")
    assert r.status_code == 429
    assert "Retry-After" in r.headers
    assert int(r.headers["Retry-After"]) > 0


def test_rate_limit_exempt_health_never_429():
    """Health probes must never be blocked regardless of rate limit config."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient as TC

    mini = FastAPI()

    @mini.get("/health")
    def health():
        return {"ok": True}

    mini.add_middleware(RateLimitMiddleware, rpm=1)
    c = TC(mini)
    for _ in range(10):
        assert c.get("/health").status_code == 200


def test_rate_limit_forwarded_for():
    """X-Forwarded-For is used to identify the real client IP."""
    rl = RateLimitMiddleware.__new__(RateLimitMiddleware)
    rl._rpm = 10

    class FakeRequest:
        headers = {"X-Forwarded-For": "203.0.113.5, 10.0.0.1"}
        client = type("C", (), {"host": "10.0.0.1"})()

    ip = RateLimitMiddleware._client_ip(FakeRequest())
    assert ip == "203.0.113.5"


# ── Startup validation ────────────────────────────────────────────────────────

def test_validate_env_clean(monkeypatch):
    """All keys set to non-default values → no warnings."""
    monkeypatch.setenv("SOVEREIGN_VIEWER_KEY", "abc123valid")
    monkeypatch.setenv("SOVEREIGN_EDITOR_KEY", "def456valid")
    monkeypatch.setenv("SOVEREIGN_ADMIN_KEY", "ghi789valid")
    monkeypatch.setenv("SOVEREIGN_CERT_SECRET", "some_secret")
    monkeypatch.setenv("SOVEREIGN_EMBEDDER", "tfidf")
    monkeypatch.delenv("OLLAMA_URL", raising=False)
    warnings = validate_env()
    assert warnings == []


def test_validate_env_default_keys_warn(monkeypatch):
    monkeypatch.setenv("SOVEREIGN_VIEWER_KEY", "change_me_viewer")
    monkeypatch.setenv("SOVEREIGN_EDITOR_KEY", "change_me_editor")
    monkeypatch.setenv("SOVEREIGN_ADMIN_KEY", "change_me_admin")
    monkeypatch.setenv("SOVEREIGN_CERT_SECRET", "ok")
    monkeypatch.setenv("SOVEREIGN_EMBEDDER", "tfidf")
    warnings = validate_env()
    assert any("SOVEREIGN_VIEWER_KEY" in w for w in warnings)
    assert any("SOVEREIGN_EDITOR_KEY" in w for w in warnings)
    assert any("SOVEREIGN_ADMIN_KEY" in w for w in warnings)


def test_validate_env_missing_cert_secret_warns(monkeypatch):
    monkeypatch.setenv("SOVEREIGN_VIEWER_KEY", "v-valid")
    monkeypatch.setenv("SOVEREIGN_EDITOR_KEY", "e-valid")
    monkeypatch.setenv("SOVEREIGN_ADMIN_KEY", "a-valid")
    monkeypatch.delenv("SOVEREIGN_CERT_SECRET", raising=False)
    monkeypatch.setenv("SOVEREIGN_EMBEDDER", "tfidf")
    warnings = validate_env()
    assert any("SOVEREIGN_CERT_SECRET" in w for w in warnings)


def test_validate_env_unknown_embedder_warns(monkeypatch):
    monkeypatch.setenv("SOVEREIGN_VIEWER_KEY", "v-valid")
    monkeypatch.setenv("SOVEREIGN_EDITOR_KEY", "e-valid")
    monkeypatch.setenv("SOVEREIGN_ADMIN_KEY", "a-valid")
    monkeypatch.setenv("SOVEREIGN_CERT_SECRET", "ok")
    monkeypatch.setenv("SOVEREIGN_EMBEDDER", "unknown-model")
    warnings = validate_env()
    assert any("SOVEREIGN_EMBEDDER" in w for w in warnings)


def test_validate_env_bad_ollama_url_warns(monkeypatch):
    monkeypatch.setenv("SOVEREIGN_VIEWER_KEY", "v-valid")
    monkeypatch.setenv("SOVEREIGN_EDITOR_KEY", "e-valid")
    monkeypatch.setenv("SOVEREIGN_ADMIN_KEY", "a-valid")
    monkeypatch.setenv("SOVEREIGN_CERT_SECRET", "ok")
    monkeypatch.setenv("SOVEREIGN_EMBEDDER", "tfidf")
    monkeypatch.setenv("OLLAMA_URL", "ollama:11434")  # missing scheme
    warnings = validate_env()
    assert any("OLLAMA_URL" in w for w in warnings)


# ── Dockerfile ────────────────────────────────────────────────────────────────

def test_dockerfile_has_non_root_user():
    dockerfile = Path("Dockerfile").read_text()
    assert "USER sovereign" in dockerfile


def test_dockerfile_has_healthcheck():
    dockerfile = Path("Dockerfile").read_text()
    assert "HEALTHCHECK" in dockerfile


def test_dockerfile_multi_stage():
    dockerfile = Path("Dockerfile").read_text()
    assert dockerfile.count("FROM ") >= 2


def test_dockerfile_no_root_install():
    """pip install in runtime stage is a smell — should be done in builder."""
    lines = Path("Dockerfile").read_text().splitlines()
    runtime_section = False
    for line in lines:
        if "AS runtime" in line:
            runtime_section = True
        if runtime_section and line.strip().startswith("RUN pip install"):
            pytest.fail("pip install found in runtime stage — should be in builder stage")


# ── .env.example completeness ─────────────────────────────────────────────────

def test_env_example_has_rate_limit_var():
    env = Path(".env.example").read_text()
    assert "SOVEREIGN_RATE_LIMIT_RPM" in env


def test_env_example_has_cors_var():
    env = Path(".env.example").read_text()
    assert "SOVEREIGN_CORS_ORIGINS" in env


def test_env_example_has_cert_secret():
    env = Path(".env.example").read_text()
    assert "SOVEREIGN_CERT_SECRET" in env


# ── THIRD_PARTY.md completeness ───────────────────────────────────────────────

def test_third_party_has_optional_connectors():
    tp = Path("THIRD_PARTY.md").read_text()
    assert "snowflake-connector-python" in tp
    assert "google-cloud-bigquery" in tp
    assert "pymongo" in tp


def test_third_party_no_gpl():
    """No GPL/AGPL entry allowed per policy (LGPL driver exception OK)."""
    tp = Path("THIRD_PARTY.md").read_text().lower()
    # LGPL is allowed (driver exception), pure GPL/AGPL are not
    # Skip comment lines (#), blockquotes (>), and the policy header
    for line in tp.splitlines():
        stripped = line.strip()
        if stripped.startswith(("#", ">")):
            continue
        if "gpl" in line and "lgpl" not in line:
            pytest.fail(f"GPL dependency detected (LGPL drivers exempted): {line}")

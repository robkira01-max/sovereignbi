"""Tests pour app/security/audit.py — audit de configuration SEC-001 à SEC-006."""
import os

import pytest

from app.security.audit import SecurityFinding, audit_configuration, log_audit_results


def _run_with_env(**overrides):
    """Run audit_configuration with specific env overrides, restoring afterward."""
    saved = {k: os.environ.get(k) for k in overrides}
    for k, v in overrides.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    try:
        return audit_configuration()
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


# ---------------------------------------------------------------------------
# SEC-001 — SOVEREIGN_ADMIN_KEY
# ---------------------------------------------------------------------------

def test_sec001_missing_admin_key():
    findings = _run_with_env(SOVEREIGN_ADMIN_KEY=None, SOVEREIGN_EMBED_SECRET="x" * 32)
    codes = [f.code for f in findings]
    assert "SEC-001" in codes


def test_sec001_default_admin_key():
    findings = _run_with_env(SOVEREIGN_ADMIN_KEY="admin", SOVEREIGN_EMBED_SECRET="x" * 32)
    codes = [f.code for f in findings]
    assert "SEC-001" in codes


def test_sec001_strong_admin_key():
    findings = _run_with_env(
        SOVEREIGN_ADMIN_KEY="A-very-strong-key-not-default-2026",
        SOVEREIGN_EMBED_SECRET="x" * 32,
    )
    codes = [f.code for f in findings]
    assert "SEC-001" not in codes


# ---------------------------------------------------------------------------
# SEC-002 — SOVEREIGN_EMBED_SECRET
# ---------------------------------------------------------------------------

def test_sec002_missing_embed_secret():
    findings = _run_with_env(
        SOVEREIGN_ADMIN_KEY="strong-admin-key-ok-2026-sprint22",
        SOVEREIGN_EMBED_SECRET=None,
    )
    codes = [f.code for f in findings]
    assert "SEC-002" in codes
    match = next(f for f in findings if f.code == "SEC-002")
    assert match.severity == "critical"


def test_sec002_short_embed_secret():
    findings = _run_with_env(
        SOVEREIGN_ADMIN_KEY="strong-admin-key-ok-2026-sprint22",
        SOVEREIGN_EMBED_SECRET="tooshort",
    )
    codes = [f.code for f in findings]
    assert "SEC-002" in codes


def test_sec002_sufficient_embed_secret():
    findings = _run_with_env(
        SOVEREIGN_ADMIN_KEY="strong-admin-key-ok-2026-sprint22",
        SOVEREIGN_EMBED_SECRET="a" * 32,
    )
    codes = [f.code for f in findings]
    assert "SEC-002" not in codes


# ---------------------------------------------------------------------------
# SEC-003 — SOVEREIGN_RATE_LIMIT_RPM
# ---------------------------------------------------------------------------

def test_sec003_high_rpm_no_debug():
    findings = _run_with_env(
        SOVEREIGN_ADMIN_KEY="strong-admin-key-ok-2026-sprint22",
        SOVEREIGN_EMBED_SECRET="a" * 32,
        SOVEREIGN_RATE_LIMIT_RPM="50000",
        DEBUG="false",
    )
    codes = [f.code for f in findings]
    assert "SEC-003" in codes


def test_sec003_high_rpm_with_debug_skipped():
    # DEBUG=true → SEC-003 not raised (but SEC-004 is)
    findings = _run_with_env(
        SOVEREIGN_ADMIN_KEY="strong-admin-key-ok-2026-sprint22",
        SOVEREIGN_EMBED_SECRET="a" * 32,
        SOVEREIGN_RATE_LIMIT_RPM="50000",
        DEBUG="true",
    )
    codes = [f.code for f in findings]
    assert "SEC-003" not in codes


def test_sec003_normal_rpm():
    findings = _run_with_env(
        SOVEREIGN_ADMIN_KEY="strong-admin-key-ok-2026-sprint22",
        SOVEREIGN_EMBED_SECRET="a" * 32,
        SOVEREIGN_RATE_LIMIT_RPM="60",
        DEBUG=None,
    )
    codes = [f.code for f in findings]
    assert "SEC-003" not in codes


# ---------------------------------------------------------------------------
# SEC-004 — DEBUG
# ---------------------------------------------------------------------------

def test_sec004_debug_true():
    findings = _run_with_env(
        SOVEREIGN_ADMIN_KEY="strong-admin-key-ok-2026-sprint22",
        SOVEREIGN_EMBED_SECRET="a" * 32,
        DEBUG="true",
        SOVEREIGN_RATE_LIMIT_RPM="60",
    )
    codes = [f.code for f in findings]
    assert "SEC-004" in codes
    match = next(f for f in findings if f.code == "SEC-004")
    assert match.severity == "high"


def test_sec004_debug_false():
    findings = _run_with_env(
        SOVEREIGN_ADMIN_KEY="strong-admin-key-ok-2026-sprint22",
        SOVEREIGN_EMBED_SECRET="a" * 32,
        DEBUG="false",
        SOVEREIGN_RATE_LIMIT_RPM="60",
    )
    codes = [f.code for f in findings]
    assert "SEC-004" not in codes


# ---------------------------------------------------------------------------
# SEC-005 — OLLAMA_BASE_URL
# ---------------------------------------------------------------------------

def test_sec005_public_ollama_url():
    findings = _run_with_env(
        SOVEREIGN_ADMIN_KEY="strong-admin-key-ok-2026-sprint22",
        SOVEREIGN_EMBED_SECRET="a" * 32,
        SOVEREIGN_RATE_LIMIT_RPM="60",
        DEBUG=None,
        OLLAMA_BASE_URL="http://203.0.113.42:11434",
    )
    codes = [f.code for f in findings]
    assert "SEC-005" in codes


def test_sec005_localhost_ollama_url():
    findings = _run_with_env(
        SOVEREIGN_ADMIN_KEY="strong-admin-key-ok-2026-sprint22",
        SOVEREIGN_EMBED_SECRET="a" * 32,
        SOVEREIGN_RATE_LIMIT_RPM="60",
        DEBUG=None,
        OLLAMA_BASE_URL="http://localhost:11434",
    )
    codes = [f.code for f in findings]
    assert "SEC-005" not in codes


# ---------------------------------------------------------------------------
# SEC-006 — clés viewer == editor
# ---------------------------------------------------------------------------

def test_sec006_identical_viewer_editor():
    findings = _run_with_env(
        SOVEREIGN_ADMIN_KEY="strong-admin-key-ok-2026-sprint22",
        SOVEREIGN_EMBED_SECRET="a" * 32,
        SOVEREIGN_RATE_LIMIT_RPM="60",
        SOVEREIGN_VIEWER_KEY="shared-key",
        SOVEREIGN_EDITOR_KEY="shared-key",
        DEBUG=None,
        OLLAMA_BASE_URL=None,
    )
    codes = [f.code for f in findings]
    assert "SEC-006" in codes
    match = next(f for f in findings if f.code == "SEC-006")
    assert match.severity == "info"


def test_sec006_distinct_viewer_editor():
    findings = _run_with_env(
        SOVEREIGN_ADMIN_KEY="strong-admin-key-ok-2026-sprint22",
        SOVEREIGN_EMBED_SECRET="a" * 32,
        SOVEREIGN_RATE_LIMIT_RPM="60",
        SOVEREIGN_VIEWER_KEY="viewer-key-ok",
        SOVEREIGN_EDITOR_KEY="editor-key-ok",
        DEBUG=None,
        OLLAMA_BASE_URL=None,
    )
    codes = [f.code for f in findings]
    assert "SEC-006" not in codes


# ---------------------------------------------------------------------------
# log_audit_results — no exception
# ---------------------------------------------------------------------------

def test_log_audit_results_no_findings():
    log_audit_results([])  # must not raise


def test_log_audit_results_with_findings():
    f = SecurityFinding(
        severity="critical",
        code="SEC-001",
        title="Test",
        detail="detail",
        remediation="fix it",
    )
    log_audit_results([f])  # must not raise

"""Tests d'isolation réseau : vérifier que le code ne sort pas du périmètre."""
import os

import pytest

os.environ.setdefault("SOVEREIGN_EMBEDDER", "tfidf")


# ── OllamaClient: URL configurable ───────────────────────────────────────────

def test_ollama_url_is_configurable(monkeypatch):
    monkeypatch.setenv("OLLAMA_URL", "http://custom-ollama:11434")
    from importlib import reload
    import app.llm.ollama_client as m
    reload(m)
    client = m.OllamaClient()
    assert client.url == "http://custom-ollama:11434"
    reload(m)  # restore


def test_ollama_url_default_is_localhost(monkeypatch):
    monkeypatch.delenv("OLLAMA_URL", raising=False)
    from importlib import reload
    import app.llm.ollama_client as m
    reload(m)
    client = m.OllamaClient()
    assert "localhost" in client.url or "127.0.0.1" in client.url
    reload(m)


def test_ollama_url_custom_per_instance():
    from app.llm.ollama_client import OllamaClient
    client = OllamaClient(url="http://my-ollama:9999")
    assert client.url == "http://my-ollama:9999"


# ── No hardcoded external URLs in app/ ───────────────────────────────────────

def test_no_hardcoded_external_urls_in_app():
    """Scan app/**/*.py for hardcoded external URLs (not localhost/127.0.0.1)."""
    import re
    from pathlib import Path

    # Pattern: http(s)://something that is NOT localhost/127.0.0.1/ollama
    # officeapps.live.com: Microsoft Office.js CDN — needed for the Excel add-in CORS config
    # data.humdata.org: HDX default base URL, overridable via SOVEREIGN_HDX_URL env var
    _EXTERNAL_URL_RE = re.compile(
        r'https?://(?!localhost|127\.0\.0\.1|ollama|[a-z.]*officeapps\.live\.com|data\.humdata\.org|{)[^\s\'"#)]+'
    )
    _COMMENT_RE = re.compile(r'^\s*#')

    app_dir = Path(__file__).parent.parent / "app"
    violations = []
    for py_file in app_dir.rglob("*.py"):
        for i, line in enumerate(py_file.read_text(encoding="utf-8").splitlines(), 1):
            if _COMMENT_RE.match(line):
                continue
            if '"""' in line or "'''" in line:
                continue
            for m in _EXTERNAL_URL_RE.finditer(line):
                violations.append(f"{py_file}:{i}: {m.group()}")

    assert violations == [], f"Hardcoded external URLs found:\n" + "\n".join(violations)


# ── sql_guard: LIMIT forced ───────────────────────────────────────────────────

def test_sql_guard_forces_limit():
    from app.security.sql_guard import validate_sql

    sql = "SELECT * FROM ventes"
    result = validate_sql(sql, {"ventes"})
    assert "LIMIT" in result.upper()


def test_sql_guard_respects_existing_limit():
    from app.security.sql_guard import validate_sql

    sql = "SELECT * FROM ventes LIMIT 10"
    result = validate_sql(sql, {"ventes"})
    assert "LIMIT" in result.upper()


# ── OllamaClient circuit breaker ─────────────────────────────────────────────

def test_ollama_circuit_breaker(monkeypatch):
    """OllamaClient raises an exception after failures (no infinite retry)."""
    import httpx
    from app.llm.ollama_client import OllamaClient

    call_count = 0

    def mock_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        raise httpx.ConnectError("Connection refused")

    monkeypatch.setattr(httpx, "post", mock_post)

    client = OllamaClient(url="http://localhost:11434")
    with pytest.raises(httpx.ConnectError):
        client.complete("system", "user")

    # Should fail immediately, not retry (single call)
    assert call_count == 1


# ── App imports no external packages ─────────────────────────────────────────

def test_app_does_not_import_tools():
    """app/ must not import tools/ (CI guard, complements test_no_external_calls_in_app.py)."""
    from pathlib import Path
    import ast

    app_dir = Path(__file__).parent.parent / "app"
    for py_file in app_dir.rglob("*.py"):
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.ImportFrom) and node.module:
                    assert not node.module.startswith("tools"), \
                        f"{py_file}: imports from tools/ (forbidden)"
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        assert not alias.name.startswith("tools"), \
                            f"{py_file}: imports tools/ (forbidden)"

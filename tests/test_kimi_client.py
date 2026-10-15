"""Tests pour KimiClient et la factory get_llm_client."""
import os
from unittest.mock import MagicMock

import httpx
import pytest

os.environ.setdefault("SOVEREIGN_EMBEDDER", "tfidf")


# ── KimiClient ────────────────────────────────────────────────────────────────

def _kimi_env(monkeypatch):
    monkeypatch.setenv("KIMI_BASE_URL", "http://kimi-test.internal/v1")
    monkeypatch.setenv("KIMI_API_KEY", "test-key-abc")
    monkeypatch.setenv("KIMI_MODEL", "kimi-k3")


def _mock_response(content: str):
    """Build a mock httpx.Response that satisfies raise_for_status() + .json()."""
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"choices": [{"message": {"content": content}}]}
    return resp


def test_kimi_complete_success(monkeypatch):
    _kimi_env(monkeypatch)
    from app.llm.kimi_client import KimiClient

    def fake_post(url, **kwargs):
        return _mock_response("SELECT * FROM ventes LIMIT 100")

    monkeypatch.setattr(httpx, "post", fake_post)
    client = KimiClient()
    result = client.complete("system prompt", "user prompt")
    assert result == "SELECT * FROM ventes LIMIT 100"


def test_kimi_sends_correct_payload(monkeypatch):
    _kimi_env(monkeypatch)
    from app.llm.kimi_client import KimiClient

    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None, **kwargs):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return _mock_response("ok")

    monkeypatch.setattr(httpx, "post", fake_post)
    client = KimiClient()
    client.complete("sys", "usr")

    assert captured["url"] == "http://kimi-test.internal/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer test-key-abc"
    assert captured["json"]["model"] == "kimi-k3"
    assert captured["json"]["temperature"] == 0
    msgs = captured["json"]["messages"]
    assert msgs[0] == {"role": "system", "content": "sys"}
    assert msgs[1] == {"role": "user", "content": "usr"}


def test_kimi_raises_without_base_url(monkeypatch):
    monkeypatch.delenv("KIMI_BASE_URL", raising=False)
    monkeypatch.setenv("KIMI_API_KEY", "key")
    from importlib import reload
    import app.llm.kimi_client as m
    reload(m)
    with pytest.raises(RuntimeError, match="KIMI_BASE_URL"):
        m.KimiClient()
    reload(m)


def test_kimi_raises_without_api_key(monkeypatch):
    monkeypatch.setenv("KIMI_BASE_URL", "http://kimi-test.internal/v1")
    monkeypatch.delenv("KIMI_API_KEY", raising=False)
    from importlib import reload
    import app.llm.kimi_client as m
    reload(m)
    with pytest.raises(RuntimeError, match="KIMI_API_KEY"):
        m.KimiClient()
    reload(m)


def test_kimi_circuit_breaker_propagates_error(monkeypatch):
    """HTTP errors are raised immediately — no silent swallowing."""
    _kimi_env(monkeypatch)
    from app.llm.kimi_client import KimiClient

    call_count = 0

    def fake_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        raise httpx.ConnectError("refused")

    monkeypatch.setattr(httpx, "post", fake_post)
    client = KimiClient()
    with pytest.raises(httpx.ConnectError):
        client.complete("s", "u")
    assert call_count == 1


def test_kimi_uses_custom_model(monkeypatch):
    _kimi_env(monkeypatch)
    monkeypatch.setenv("KIMI_MODEL", "kimi-k3-turbo")
    from importlib import reload
    import app.llm.kimi_client as m
    reload(m)

    captured = {}

    def fake_post(url, json=None, **kwargs):
        captured["model"] = (json or {}).get("model")
        return _mock_response("ok")

    monkeypatch.setattr(httpx, "post", fake_post)
    m.KimiClient().complete("s", "u")
    assert captured["model"] == "kimi-k3-turbo"
    reload(m)


# ── get_llm_client factory ────────────────────────────────────────────────────

def test_factory_returns_ollama_by_default(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    from importlib import reload
    import app.llm as llm_pkg
    reload(llm_pkg)
    from app.llm.ollama_client import OllamaClient
    client = llm_pkg.get_llm_client()
    assert isinstance(client, OllamaClient)


def test_factory_returns_ollama_when_explicit(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    from importlib import reload
    import app.llm as llm_pkg
    reload(llm_pkg)
    from app.llm.ollama_client import OllamaClient
    client = llm_pkg.get_llm_client()
    assert isinstance(client, OllamaClient)


def test_factory_returns_kimi_when_set(monkeypatch):
    # Since H4, LLM_PROVIDER=kimi returns FallbackLLMClient (Kimi + circuit-breaker → Ollama).
    # The inner primary client must be a KimiClient.
    monkeypatch.setenv("LLM_PROVIDER", "kimi")
    _kimi_env(monkeypatch)
    from importlib import reload
    import app.llm as llm_pkg
    reload(llm_pkg)
    import app.llm.kimi_client as km
    reload(km)
    from app.llm.kimi_client import KimiClient
    from app.llm.fallback_client import FallbackLLMClient
    client = llm_pkg.get_llm_client()
    assert isinstance(client, FallbackLLMClient), "LLM_PROVIDER=kimi doit retourner FallbackLLMClient"
    assert isinstance(client._kimi, KimiClient), "Le client primaire doit être KimiClient"


# ── startup warnings ──────────────────────────────────────────────────────────

def test_startup_warns_missing_kimi_base_url(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "kimi")
    monkeypatch.delenv("KIMI_BASE_URL", raising=False)
    monkeypatch.setenv("KIMI_API_KEY", "key")
    from app.startup import validate_env
    warns = validate_env()
    assert any("KIMI_BASE_URL" in w for w in warns)


def test_startup_warns_missing_kimi_api_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "kimi")
    monkeypatch.setenv("KIMI_BASE_URL", "http://kimi-test.internal/v1")
    monkeypatch.delenv("KIMI_API_KEY", raising=False)
    from app.startup import validate_env
    warns = validate_env()
    assert any("KIMI_API_KEY" in w for w in warns)


def test_startup_no_kimi_warnings_when_configured(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "kimi")
    monkeypatch.setenv("KIMI_BASE_URL", "http://kimi-test.internal/v1")
    monkeypatch.setenv("KIMI_API_KEY", "key")
    from app.startup import validate_env
    warns = validate_env()
    assert not any("KIMI" in w for w in warns)


def test_startup_warns_unknown_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gpt999")
    from app.startup import validate_env
    warns = validate_env()
    assert any("inconnu" in w for w in warns)

"""Tests for Sprint H4 — Kimi circuit breaker + Ollama fallback."""
import os
from unittest.mock import MagicMock, patch

import pytest


def _make_fallback(**env_overrides):
    """Build a FallbackLLMClient with patched Kimi env vars."""
    env = {
        "KIMI_BASE_URL": "https://api.kimi.test",
        "KIMI_API_KEY": "test-key",
        "KIMI_MODEL": "kimi-k3",
        **env_overrides,
    }
    with patch.dict(os.environ, env):
        from app.llm.fallback_client import FallbackLLMClient
        return FallbackLLMClient()


def test_routes_to_kimi_when_healthy():
    client = _make_fallback()
    client._kimi.complete = MagicMock(return_value="kimi_answer")
    client._ollama.complete = MagicMock(return_value="ollama_answer")
    assert client.complete("sys", "user") == "kimi_answer"
    client._kimi.complete.assert_called_once()
    client._ollama.complete.assert_not_called()


def test_falls_back_on_single_kimi_error():
    client = _make_fallback()
    client._kimi.complete = MagicMock(side_effect=Exception("timeout"))
    client._ollama.complete = MagicMock(return_value="fallback")
    result = client.complete("sys", "user")
    assert result == "fallback"


def test_circuit_opens_after_max_failures():
    with patch.dict(os.environ, {"KIMI_CB_MAX_FAILURES": "3"}):
        client = _make_fallback()
        client._kimi.complete = MagicMock(side_effect=Exception("error"))
        client._ollama.complete = MagicMock(return_value="fallback")
        for _ in range(3):
            client.complete("sys", "user")
    assert client._circuit_open


def test_circuit_open_routes_to_ollama_without_kimi_call():
    client = _make_fallback()
    client._kimi.complete = MagicMock(side_effect=Exception("error"))
    client._ollama.complete = MagicMock(return_value="fallback")
    # Force open
    for _ in range(3):
        client.complete("sys", "user")
    client._kimi.complete.reset_mock()
    # Now circuit is open
    result = client.complete("sys", "user")
    assert result == "fallback"
    client._kimi.complete.assert_not_called()


def test_circuit_resets_on_success():
    client = _make_fallback()
    client._kimi.complete = MagicMock(side_effect=Exception("err"))
    client._ollama.complete = MagicMock(return_value="x")
    # Trigger 2 failures (less than max)
    for _ in range(2):
        client.complete("sys", "user")
    # Now kimi recovers
    client._kimi.complete = MagicMock(return_value="recovered")
    result = client.complete("sys", "user")
    assert result == "recovered"
    assert client._failures == 0


def test_circuit_status_closed():
    client = _make_fallback()
    client._kimi.complete = MagicMock(return_value="ok")
    client.complete("sys", "user")
    status = client.circuit_status()
    assert status["circuit_open"] is False
    assert status["provider"] == "kimi"


def test_circuit_status_open():
    client = _make_fallback()
    client._kimi.complete = MagicMock(side_effect=Exception("err"))
    client._ollama.complete = MagicMock(return_value="x")
    for _ in range(3):
        client.complete("sys", "user")
    status = client.circuit_status()
    assert status["circuit_open"] is True


def test_failures_counter_increments():
    client = _make_fallback()
    client._kimi.complete = MagicMock(side_effect=Exception("err"))
    client._ollama.complete = MagicMock(return_value="x")
    client.complete("sys", "user")
    assert client._failures == 1


def test_factory_returns_fallback_for_kimi():
    env = {
        "LLM_PROVIDER": "kimi",
        "KIMI_BASE_URL": "https://api.kimi.test",
        "KIMI_API_KEY": "key",
    }
    with patch.dict(os.environ, env):
        from app.llm import get_llm_client
        from app.llm.fallback_client import FallbackLLMClient
        import importlib
        import app.llm
        importlib.reload(app.llm)
        client = app.llm.get_llm_client()
        assert isinstance(client, FallbackLLMClient)


def test_factory_returns_ollama_by_default():
    with patch.dict(os.environ, {"LLM_PROVIDER": "ollama"}):
        from app.llm.ollama_client import OllamaClient
        import importlib
        import app.llm
        importlib.reload(app.llm)
        client = app.llm.get_llm_client()
        assert isinstance(client, OllamaClient)

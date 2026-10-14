"""Circuit-breaker wrapper for KimiClient → falls back to OllamaClient.

When LLM_PROVIDER=kimi:
  - Calls are routed to KimiClient by default.
  - After KIMI_CB_MAX_FAILURES (default 3) consecutive errors, the circuit
    opens and calls are routed to OllamaClient for KIMI_CB_RESET_SECONDS
    (default 300 s = 5 min).
  - When the circuit is open, the first call after the reset window is a
    probe: if it succeeds, the circuit closes; if it fails, the window
    resets.
  - All circuit state changes are logged to stderr (structured one-liners).
"""
from __future__ import annotations

import os
import sys
import threading
import time

from app.llm.ollama_client import LLM, OllamaClient


_MAX_FAILURES = int(os.environ.get("KIMI_CB_MAX_FAILURES", "3"))
_RESET_SECONDS = float(os.environ.get("KIMI_CB_RESET_SECONDS", "300"))


def _log(event: str, **kwargs) -> None:
    parts = " ".join(f"{k}={v}" for k, v in kwargs.items())
    print(f"[fallback_llm] event={event} {parts}", file=sys.stderr, flush=True)


class FallbackLLMClient:
    """KimiClient with circuit-breaker that falls back to OllamaClient."""

    def __init__(self) -> None:
        from app.llm.kimi_client import KimiClient

        self._kimi = KimiClient()
        self._ollama = OllamaClient()
        self._failures = 0
        self._open_until: float = 0.0
        self._lock = threading.Lock()

    @property
    def _circuit_open(self) -> bool:
        if self._open_until and time.monotonic() < self._open_until:
            return True
        return False

    def _open_circuit(self) -> None:
        self._open_until = time.monotonic() + _RESET_SECONDS
        _log("circuit_open", failures=self._failures, reset_in=f"{_RESET_SECONDS}s")

    def _reset_circuit(self) -> None:
        self._failures = 0
        self._open_until = 0.0
        _log("circuit_closed", provider="kimi")

    def complete(self, system: str, user: str) -> str:
        with self._lock:
            use_fallback = self._circuit_open

        if use_fallback:
            _log("routing", provider="ollama", reason="circuit_open")
            return self._ollama.complete(system, user)

        try:
            result = self._kimi.complete(system, user)
            with self._lock:
                if self._failures > 0:
                    self._reset_circuit()
            return result
        except Exception as exc:
            with self._lock:
                self._failures += 1
                _log("kimi_error", failures=self._failures, error=str(exc)[:120])
                if self._failures >= _MAX_FAILURES:
                    self._open_circuit()
            # Fall back for this call too
            _log("routing", provider="ollama", reason="kimi_failed")
            return self._ollama.complete(system, user)

    def circuit_status(self) -> dict:
        with self._lock:
            return {
                "provider": "kimi",
                "circuit_open": self._circuit_open,
                "failures": self._failures,
                "reset_at": self._open_until or None,
            }


# satisfy the type checker
_: LLM = FallbackLLMClient.__new__(FallbackLLMClient)  # type: ignore[assignment]

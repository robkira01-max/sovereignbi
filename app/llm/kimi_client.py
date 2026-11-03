"""OpenAI-compatible LLM client for Kimi K3 (or any OpenAI-compatible API).

Required env vars when LLM_PROVIDER=kimi:
  KIMI_BASE_URL  — API base URL, no trailing slash (see provider documentation)
  KIMI_API_KEY   — API key for Bearer auth
  KIMI_MODEL     — model name (default: kimi-k3)
  KIMI_TIMEOUT   — request timeout in seconds (default: 60)

No URL is hardcoded here — the caller must set KIMI_BASE_URL.
"""
import datetime
import os
import threading

import httpx

from app.llm.ollama_client import LLM  # re-use the Protocol

# 02/03 — Plafond de dépenses quotidien (en mémoire, RAZ chaque jour UTC).
_COST_PER_1K_TOKENS = float(os.environ.get("KIMI_COST_PER_1K_TOKENS", "0.012"))
_DAILY_BUDGET_USD = float(os.environ.get("KIMI_DAILY_BUDGET_USD", "5.0"))
_cost_lock = threading.Lock()
_daily_spend: float = 0.0
_spend_day: int = -1


class KimiBudgetExceededError(RuntimeError):
    """Raised when the daily API spend cap (KIMI_DAILY_BUDGET_USD) is reached."""


def _check_and_record_cost(prompt: str, response: str) -> None:
    global _daily_spend, _spend_day
    today = datetime.datetime.now(datetime.timezone.utc).day
    tokens = max(1, len(prompt) // 4) + max(1, len(response) // 4)
    cost = tokens * _COST_PER_1K_TOKENS / 1000
    with _cost_lock:
        if today != _spend_day:
            _daily_spend = 0.0
            _spend_day = today
        if _daily_spend + cost > _DAILY_BUDGET_USD:
            raise KimiBudgetExceededError(
                f"Plafond quotidien API atteint ({_DAILY_BUDGET_USD:.2f} USD/j). "
                "Réessayez demain ou augmentez KIMI_DAILY_BUDGET_USD."
            )
        _daily_spend += cost


class KimiClient:
    """OpenAI-compatible LLM client (chat/completions endpoint)."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
    ) -> None:
        resolved_url = base_url or os.environ.get("KIMI_BASE_URL", "")
        if not resolved_url:
            raise RuntimeError(
                "KIMI_BASE_URL est obligatoire quand LLM_PROVIDER=kimi. "
                "Définissez cette variable d'environnement avant de démarrer."
            )
        resolved_key = api_key or os.environ.get("KIMI_API_KEY", "")
        if not resolved_key:
            raise RuntimeError(
                "KIMI_API_KEY est obligatoire quand LLM_PROVIDER=kimi. "
                "Définissez cette variable d'environnement avant de démarrer."
            )

        self.base_url = resolved_url.rstrip("/")
        self._api_key = resolved_key
        self.model = model or os.environ.get("KIMI_MODEL", "kimi-k3")
        self.timeout = float(timeout or os.environ.get("KIMI_TIMEOUT", "60"))

    def complete(self, system: str, user: str) -> str:
        r = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "temperature": 0,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
            timeout=self.timeout,
        )
        r.raise_for_status()
        text = r.json()["choices"][0]["message"]["content"]
        _check_and_record_cost(system + user, text)
        return text


# satisfy the type checker
_: LLM = KimiClient.__new__(KimiClient)  # type: ignore[assignment]

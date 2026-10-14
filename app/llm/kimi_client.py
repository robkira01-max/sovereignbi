"""OpenAI-compatible LLM client for Kimi K3 (or any OpenAI-compatible API).

Required env vars when LLM_PROVIDER=kimi:
  KIMI_BASE_URL  — API base URL, no trailing slash (see provider documentation)
  KIMI_API_KEY   — API key for Bearer auth
  KIMI_MODEL     — model name (default: kimi-k3)
  KIMI_TIMEOUT   — request timeout in seconds (default: 60)

No URL is hardcoded here — the caller must set KIMI_BASE_URL.
"""
import os

import httpx

from app.llm.ollama_client import LLM  # re-use the Protocol


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
        return r.json()["choices"][0]["message"]["content"]


# satisfy the type checker
_: LLM = KimiClient.__new__(KimiClient)  # type: ignore[assignment]

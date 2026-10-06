"""Client LLM local. Aucun appel hors du serveur Ollama configuré."""
import os
from typing import Protocol

import httpx


class LLM(Protocol):
    def complete(self, system: str, user: str) -> str: ...


class OllamaClient:
    def __init__(self, url: str | None = None, model: str | None = None, timeout: float = 300.0):
        self.url = (url or os.environ.get("OLLAMA_URL", "http://localhost:11434")).rstrip("/")
        self.model = model or os.environ.get("LLM_MODEL", "qwen2.5-coder:32b")
        self.timeout = timeout

    def complete(self, system: str, user: str) -> str:
        r = httpx.post(
            f"{self.url}/api/chat",
            json={
                "model": self.model,
                "stream": False,
                "options": {"temperature": 0},
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()["message"]["content"]

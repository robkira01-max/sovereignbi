"""LLM client factory.

Set LLM_PROVIDER=kimi to use the Kimi K3 OpenAI-compatible API.
Default (or LLM_PROVIDER=ollama) uses the local Ollama server.
"""
import os

from app.llm.ollama_client import LLM, OllamaClient


def get_llm_client() -> LLM:
    """Return the configured LLM client based on LLM_PROVIDER env var.

    LLM_PROVIDER=kimi  → FallbackLLMClient (KimiClient + circuit-breaker → OllamaClient)
    LLM_PROVIDER=ollama (default) → OllamaClient
    """
    provider = os.environ.get("LLM_PROVIDER", "ollama").lower().strip()
    if provider == "kimi":
        from app.llm.fallback_client import FallbackLLMClient
        return FallbackLLMClient()
    return OllamaClient()

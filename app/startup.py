"""Startup validation — warn on missing or default env vars."""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_DEFAULT_KEYS = {"change_me_viewer", "change_me_editor", "change_me_admin"}


def validate_env() -> list[str]:
    """Check environment variables at boot. Return list of warning strings."""
    warnings: list[str] = []

    for role in ("viewer", "editor", "admin"):
        var = f"SOVEREIGN_{role.upper()}_KEY"
        val = os.environ.get(var, "")
        if not val:
            warnings.append(f"{var} non définie — authentification {role!r} désactivée")
        elif val in _DEFAULT_KEYS or val.startswith("change_me"):
            warnings.append(f"{var} utilise la valeur par défaut — à changer avant mise en production")

    cert_secret = os.environ.get("SOVEREIGN_CERT_SECRET", "")
    if not cert_secret:
        warnings.append(
            "SOVEREIGN_CERT_SECRET non définie — "
            "les certificats de précision ne seront pas signés (HMAC désactivé)"
        )

    embedder = os.environ.get("SOVEREIGN_EMBEDDER", "tfidf")
    if embedder not in ("tfidf", "bge-m3"):
        warnings.append(
            f"SOVEREIGN_EMBEDDER={embedder!r} inconnu — "
            "valeurs acceptées : 'tfidf' (sans réseau) ou 'bge-m3' (production)"
        )

    provider = os.environ.get("LLM_PROVIDER", "ollama").lower()
    if provider == "ollama":
        ollama_url = os.environ.get("OLLAMA_URL", "") or os.environ.get("OLLAMA_BASE_URL", "")
        if ollama_url and not ollama_url.startswith(("http://", "https://")):
            warnings.append(f"OLLAMA_URL={ollama_url!r} — doit commencer par http:// ou https://")
    elif provider == "kimi":
        if not os.environ.get("KIMI_BASE_URL"):
            warnings.append("KIMI_BASE_URL non définie — requis quand LLM_PROVIDER=kimi")
        if not os.environ.get("KIMI_API_KEY"):
            warnings.append("KIMI_API_KEY non définie — requis quand LLM_PROVIDER=kimi")
    else:
        warnings.append(
            f"LLM_PROVIDER={provider!r} inconnu — valeurs acceptées : 'ollama' ou 'kimi'"
        )

    return warnings


def log_startup_warnings(warnings: list[str]) -> None:
    """Log each warning at WARNING level; log OK at INFO if none."""
    for w in warnings:
        logger.warning("[startup] %s", w)
    if not warnings:
        logger.info("[startup] Configuration validée — aucun avertissement")

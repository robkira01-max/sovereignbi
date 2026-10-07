"""Utilitaires de génération et validation de clés API."""
from __future__ import annotations

import hashlib
import os
import secrets
import string

_KEY_ALPHABET = string.ascii_letters + string.digits + "-_"
_MIN_ENTROPY_LENGTH = 32


def generate_api_key(prefix: str = "sk") -> str:
    """Génère une clé API aléatoire de 40 caractères avec préfixe."""
    body = "".join(secrets.choice(_KEY_ALPHABET) for _ in range(40))
    return f"{prefix}_{body}"


def hash_key_for_log(key: str) -> str:
    """Retourne les 8 premiers caractères SHA-256 hex d'une clé — safe pour les logs."""
    digest = hashlib.sha256(key.encode()).hexdigest()
    return digest[:8] + "..."


def validate_key_strength(key: str) -> tuple[bool, str]:
    """Valide qu'une clé est suffisamment robuste.

    Returns (ok, reason). ok=True si la clé passe tous les critères.
    """
    if not key:
        return False, "La clé est vide."
    if len(key) < _MIN_ENTROPY_LENGTH:
        return False, f"La clé fait {len(key)} caractères (minimum {_MIN_ENTROPY_LENGTH})."
    has_upper = any(c.isupper() for c in key)
    has_lower = any(c.islower() for c in key)
    has_digit = any(c.isdigit() for c in key)
    if not (has_upper and has_lower and has_digit):
        return False, "La clé doit contenir des majuscules, minuscules et chiffres."
    # Détecte les clés trop répétitives (entropie faible)
    unique_ratio = len(set(key)) / len(key)
    if unique_ratio < 0.3:
        return False, "La clé a trop peu de caractères uniques (entropie insuffisante)."
    return True, "OK"

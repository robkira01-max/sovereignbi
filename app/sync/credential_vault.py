"""Credential vault — chiffrement AES-256 (Fernet) des mots de passe de connexion."""
from __future__ import annotations

import base64
import os
import warnings

from cryptography.fernet import Fernet

VAULT_KEY_ENV = "SOVEREIGN_VAULT_KEY"
_DEV_KEY_BYTES = b"sovereignbi-dev-vault-key-32byt"


def _get_fernet() -> Fernet:
    raw = os.environ.get(VAULT_KEY_ENV, "").encode()
    if not raw:
        app_env = os.environ.get("APP_ENV", "development").lower()
        if app_env == "production":
            raise RuntimeError(
                f"{VAULT_KEY_ENV} est obligatoire en production. "
                "Générer : python3 -c \"import os,base64; print(base64.urlsafe_b64encode(os.urandom(32)).decode())\""
            )
        warnings.warn(
            f"{VAULT_KEY_ENV} non définie — clé de dev utilisée. "
            "Définir cette variable en production.",
            RuntimeWarning,
            stacklevel=3,
        )
        raw = _DEV_KEY_BYTES
    raw32 = (raw + b"0" * 32)[:32]
    fernet_key = base64.urlsafe_b64encode(raw32)
    return Fernet(fernet_key)


def encrypt_credential(plaintext: str) -> str:
    """Chiffrer un credential. Retourne une chaîne base64 Fernet."""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_credential(ciphertext: str) -> str:
    """Déchiffrer un credential chiffré par encrypt_credential."""
    return _get_fernet().decrypt(ciphertext.encode()).decode()

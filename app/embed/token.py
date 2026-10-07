"""Tokens d'intégration signés HMAC-SHA256 pour iframe/embed."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass

EMBED_SECRET_ENV = "SOVEREIGN_EMBED_SECRET"


@dataclass
class EmbedToken:
    token: str
    dashboard_id: str
    expires_at: int
    scopes: list[str]


def _get_secret(secret: str | None) -> str:
    s = secret or os.environ.get(EMBED_SECRET_ENV, "")
    if not s:
        raise ValueError(
            f"Secret d'embed manquant. Définir {EMBED_SECRET_ENV} ou passer secret=."
        )
    return s


def generate_token(
    dashboard_id: str = "*",
    ttl_seconds: int = 3600,
    scopes: list[str] = ("read",),
    secret: str | None = None,
) -> EmbedToken:
    s = _get_secret(secret)
    expires_at = int(time.time()) + ttl_seconds
    payload = {
        "dashboard_id": dashboard_id,
        "expires_at": expires_at,
        "scopes": list(scopes),
    }
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode()
    payload_b64 = base64.urlsafe_b64encode(payload_bytes).rstrip(b"=").decode()
    sig = hmac.new(s.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
    token = f"{payload_b64}.{sig}"
    return EmbedToken(
        token=token,
        dashboard_id=dashboard_id,
        expires_at=expires_at,
        scopes=list(scopes),
    )


def verify_token(token: str, secret: str | None = None) -> EmbedToken | None:
    try:
        s = _get_secret(secret)
        parts = token.rsplit(".", 1)
        if len(parts) != 2:
            return None
        payload_b64, sig = parts
        expected_sig = hmac.new(s.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return None
        padding = 4 - len(payload_b64) % 4
        payload_bytes = base64.urlsafe_b64decode(payload_b64 + "=" * (padding % 4))
        payload = json.loads(payload_bytes)
        if int(time.time()) > payload["expires_at"]:
            return None
        return EmbedToken(
            token=token,
            dashboard_id=payload["dashboard_id"],
            expires_at=payload["expires_at"],
            scopes=payload.get("scopes", ["read"]),
        )
    except Exception:
        return None

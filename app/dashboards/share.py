"""Dashboard share tokens — HMAC-SHA256-based, time-limited, opaque."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from pathlib import Path

_SHARES_PATH = Path("data/shares.json")
_SHARE_SECRET = os.environ.get("SHARE_SECRET", "dev-share-secret-change-in-prod")
_DEFAULT_TTL = 7 * 24 * 3600  # 7 days


def _load(path: Path | None = None) -> dict[str, dict]:
    p = path if path is not None else _SHARES_PATH
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save(data: dict[str, dict], path: Path | None = None) -> None:
    p = path if path is not None else _SHARES_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _make_token(dashboard_id: str, expires_at: int) -> str:
    msg = f"{dashboard_id}:{expires_at}".encode()
    sig = hmac.new(_SHARE_SECRET.encode(), msg, hashlib.sha256).hexdigest()
    return f"{dashboard_id}.{expires_at}.{sig}"


def generate_share_token(
    dashboard_id: str,
    ttl: int = _DEFAULT_TTL,
    path: Path | None = None,
) -> dict:
    """Create a share record and return {token, expires_at}."""
    expires_at = int(time.time()) + ttl
    token = _make_token(dashboard_id, expires_at)
    data = _load(path)
    data[token] = {"dashboard_id": dashboard_id, "expires_at": expires_at}
    _save(data, path)
    return {"token": token, "dashboard_id": dashboard_id, "expires_at": expires_at}


def validate_share_token(token: str, path: Path | None = None) -> str | None:
    """Return dashboard_id if token is valid and not expired, else None."""
    data = _load(path)
    record = data.get(token)
    if record is None:
        return None
    if time.time() > record["expires_at"]:
        return None
    # Re-verify HMAC to protect against file tampering
    expected = _make_token(record["dashboard_id"], record["expires_at"])
    if not hmac.compare_digest(token, expected):
        return None
    return record["dashboard_id"]


def revoke_share_token(token: str, path: Path | None = None) -> bool:
    """Remove a share token. Returns True if it existed."""
    data = _load(path)
    if token not in data:
        return False
    del data[token]
    _save(data, path)
    return True

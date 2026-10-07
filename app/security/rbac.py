"""RBAC minimal : viewer < editor < admin.

Clés configurées via variables d'environnement :
  SOVEREIGN_VIEWER_KEY, SOVEREIGN_EDITOR_KEY, SOVEREIGN_ADMIN_KEY

Si une variable n'est pas définie, aucune clé ne correspond à ce rôle.
"""
import os

from fastapi import Header, HTTPException

ROLES: dict[str, int] = {"viewer": 0, "editor": 1, "admin": 2}


def get_role_from_key(api_key: str) -> str | None:
    """Return the role for api_key, or None if unrecognised."""
    for role in ("admin", "editor", "viewer"):
        env_val = os.environ.get(f"SOVEREIGN_{role.upper()}_KEY", "")
        if env_val and api_key == env_val:
            return role
    return None


class RequireRole:
    """FastAPI dependency: raises 401/403 if caller's role is below min_role."""

    def __init__(self, min_role: str) -> None:
        if min_role not in ROLES:
            raise ValueError(f"Unknown role: {min_role!r}")
        self.min_level = ROLES[min_role]
        self.min_role = min_role

    def __call__(self, x_api_key: str = Header(default="")) -> str:
        role = get_role_from_key(x_api_key)
        if role is None:
            raise HTTPException(401, "Clé API manquante ou invalide.")
        if ROLES[role] < self.min_level:
            raise HTTPException(403, f"Rôle {self.min_role!r} requis.")
        return role

"""RBAC minimal : viewer < editor < admin.

Accepte deux formes d'authentification :
  1. X-Api-Key: <key>               (accès API direct, clés en variables d'env)
  2. Authorization: Bearer <token>  (session web email+mot de passe)
"""
import hmac
import os

from fastapi import Header, HTTPException

ROLES: dict[str, int] = {"viewer": 0, "editor": 1, "admin": 2}


def get_role_from_key(api_key: str) -> str | None:
    given = api_key.encode()
    found: str | None = None
    for role in ("admin", "editor", "viewer"):  # no early exit: constant work per call
        env_val = os.environ.get(f"SOVEREIGN_{role.upper()}_KEY", "")
        if env_val and hmac.compare_digest(given, env_val.encode()) and found is None:
            found = role
    return found


class RequireRole:
    def __init__(self, min_role: str) -> None:
        if min_role not in ROLES:
            raise ValueError(f"Unknown role: {min_role!r}")
        self.min_level = ROLES[min_role]
        self.min_role = min_role

    def __call__(
        self,
        x_api_key: str = Header(default=""),
        authorization: str | None = Header(default=None),
    ) -> str:
        # 1. Try X-Api-Key (backward compat for API integrations)
        if x_api_key:
            role = get_role_from_key(x_api_key)
            if role is None:
                raise HTTPException(401, "Clé API invalide.")
            if ROLES[role] < self.min_level:
                raise HTTPException(403, f"Rôle {self.min_role!r} requis.")
            return role

        # 2. Try Bearer session token (web login)
        if authorization and authorization.startswith("Bearer "):
            from app.auth.security import verify_session  # lazy to avoid circular
            user = verify_session(authorization[7:])
            if not user:
                raise HTTPException(401, "Session expirée ou invalide.")
            role = user["role"]
            if role not in ROLES:  # corrupted/unknown role → deny, never default upward
                raise HTTPException(403, "Rôle utilisateur invalide.")
            if ROLES[role] < self.min_level:
                raise HTTPException(403, f"Rôle {self.min_role!r} requis.")
            return role

        raise HTTPException(401, "Authentification requise.")

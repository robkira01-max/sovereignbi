"""RBAC minimal : viewer < editor < admin.

Accepte deux formes d'authentification :
  1. X-Api-Key: <key>               (accès API direct, clés en variables d'env)
  2. Authorization: Bearer <token>  (session web email+mot de passe)
"""
import hmac
import os

from fastapi import Header, HTTPException
from starlette.concurrency import run_in_threadpool

from app.security.identity import ApiKeyRejected, Identity, current_identity

ROLES: dict[str, int] = {"viewer": 0, "editor": 1, "admin": 2}


def get_role_from_key(api_key: str) -> str | None:
    given = api_key.encode()
    found: str | None = None
    for role in ("admin", "editor", "viewer"):  # no early exit: constant work per call
        env_val = os.environ.get(f"SOVEREIGN_{role.upper()}_KEY", "")
        if env_val and hmac.compare_digest(given, env_val.encode()) and found is None:
            found = role
    return found


def resolve_api_identity(raw: str) -> Identity:
    """Clé `X-Api-Key` → identité. Lève `ApiKeyRejected` (401/403) avec un message explicite mais sans indice sur la clé."""
    from app.auth import apikeys
    from app.security import legacy_keys
    if raw.startswith(apikeys.KEY_PREFIX):
        ident = apikeys.resolve(raw)
        if ident is None:
            raise ApiKeyRejected(401, "Clé API invalide, expirée ou révoquée.")
        return ident
    role = legacy_keys.match_role(raw)
    if role is None:
        raise ApiKeyRejected(401, "Clé API invalide.")
    if legacy_keys.expired():
        raise ApiKeyRejected(401, "Clé partagée (héritée) expirée : utilisez une clé personnelle (mzb_…) créée depuis votre session.")
    effective = "viewer" if legacy_keys.read_only() else role
    return Identity("legacy_key", effective, key_ref=legacy_keys.fingerprint(raw), configured_role=role)


class RequireRole:
    """Dépendance FastAPI. `session_only=True` : l'action exige une session nominative (résolution, revue, validation)."""

    def __init__(self, min_role: str, *, session_only: bool = False) -> None:
        if min_role not in ROLES:
            raise ValueError(f"Unknown role: {min_role!r}")
        self.min_level = ROLES[min_role]
        self.min_role = min_role
        self.session_only = session_only

    async def __call__(
        self,
        x_api_key: str = Header(default=""),
        authorization: str | None = Header(default=None),
    ) -> str:
        ident = await run_in_threadpool(self._identify, x_api_key, authorization)
        current_identity.set(ident)      # lu par le journal d'audit (même tâche : visible des routes synchrones)
        return ident.role

    def _identify(self, x_api_key: str, authorization: str | None) -> Identity:
        if x_api_key:
            try:
                ident = resolve_api_identity(x_api_key)
            except ApiKeyRejected as e:
                raise HTTPException(e.status, e.message) from None
            if self.session_only:
                who = "une clé partagée (héritée), non attribuable à une personne," if ident.method == "legacy_key" else "une clé API"
                raise HTTPException(403, f"Action réservée aux sessions nominatives : {who} ne suffit pas (résolution, revue et validation exigent une connexion).")
            if ROLES[ident.role] < self.min_level:
                if ident.method == "legacy_key" and ident.configured_role and ROLES[ident.configured_role] >= self.min_level:
                    raise HTTPException(403, "Clé partagée (héritée) en lecture seule : créez une clé personnelle (mzb_…) depuis votre session.")
                raise HTTPException(403, f"Rôle {self.min_role!r} requis.")
            return ident
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
            return Identity("session", role, user_id=int(user["id"]))
        raise HTTPException(401, "Authentification requise.")

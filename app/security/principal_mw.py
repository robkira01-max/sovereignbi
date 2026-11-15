"""Middleware ASGI : identifie l'appelant pour la sécurité par ligne (P-068).

Ne fait rien (ni lecture de session, ni coût) tant qu'aucune règle n'existe. Quand des règles existent,
la clé API ou la session est résolue comme dans `RequireRole` et le principal est posé dans un ContextVar
vu par le code synchrone (copié vers le pool de threads). Authentification invalide ou absente : pas de
principal, donc accès refusé aux tables protégées ; la route renverra de toute façon 401.
"""
from __future__ import annotations

from app.security import row_policy
from app.security.rbac import get_role_from_key


def _resolve(headers: dict[bytes, bytes]) -> row_policy.Principal | None:
    key = headers.get(b"x-api-key", b"").decode("latin-1")
    if key:
        role = get_role_from_key(key)
        if role == "admin":
            return row_policy.Principal("admin")
        return row_policy.Principal("key") if role else None
    auth = headers.get(b"authorization", b"").decode("latin-1")
    if auth.startswith("Bearer "):
        from app.auth.security import verify_session
        user = verify_session(auth[7:])
        if not user:
            return None
        return row_policy.Principal("admin") if user["role"] == "admin" else row_policy.Principal("user", int(user["id"]))
    return None


class PrincipalMiddleware:
    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not row_policy.active():
            await self.app(scope, receive, send)
            return
        try:
            principal = _resolve(dict(scope.get("headers", [])))
        except Exception:  # noqa: BLE001 - base d'auth indisponible : pas d'identité = accès refusé
            principal = None
        with row_policy.as_principal(principal):
            await self.app(scope, receive, send)

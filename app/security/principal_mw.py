"""Middleware ASGI : identifie l'appelant pour la sécurité par ligne (P-068).

Ne fait rien (ni lecture de session, ni coût) tant qu'aucune règle n'existe. Quand des règles existent,
la clé API ou la session est résolue comme dans `RequireRole` et le principal est posé dans un ContextVar
vu par le code synchrone (copié vers le pool de threads). Authentification invalide ou absente : pas de
principal, donc accès refusé aux tables protégées ; la route renverra de toute façon 401.
"""
from __future__ import annotations

from app.security import row_policy
from app.security.identity import ApiKeyRejected
from app.security.rbac import resolve_api_identity


def _resolve(headers: dict[bytes, bytes]) -> row_policy.Principal | None:
    key = headers.get(b"x-api-key", b"").decode("latin-1")
    if key:
        try:
            ident = resolve_api_identity(key)
        except ApiKeyRejected:
            return None
        if ident.method == "api_key":      # clé personnelle : hérite des périmètres de son propriétaire
            return row_policy.Principal("admin") if ident.role == "admin" else row_policy.Principal("user", ident.user_id)
        return row_policy.Principal("admin") if ident.role == "admin" else row_policy.Principal("key")
    auth = headers.get(b"authorization", b"").decode("latin-1")
    if auth.startswith("Bearer "):
        from app.auth.security import verify_session
        user = verify_session(auth[7:])
        if not user:
            return None
        return row_policy.Principal("admin") if user["role"] == "admin" else row_policy.Principal("user", int(user["id"]))
    return None


def _first_headers(raw) -> dict[bytes, bytes]:
    """Première occurrence de chaque en-tête (comme `Header()` de FastAPI) : les deux décisions ne divergent jamais."""
    out: dict[bytes, bytes] = {}
    for k, v in raw:
        out.setdefault(k, v)
    return out


class PrincipalMiddleware:
    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not row_policy.active():
            await self.app(scope, receive, send)
            return
        try:
            principal = _resolve(_first_headers(scope.get("headers", [])))
        except Exception:  # noqa: BLE001 - base d'auth indisponible : pas d'identité = accès refusé
            principal = None
        with row_policy.as_principal(principal):
            await self.app(scope, receive, send)

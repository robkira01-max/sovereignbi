"""Routes d'intégration iframe via tokens HMAC-SHA256."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.dashboards.models import load_dashboard
from app.embed.token import EmbedToken, generate_token, verify_token
from app.security.rbac import RequireRole

router = APIRouter(tags=["embed"])

_ADMIN = RequireRole("admin")

DASHBOARDS_DIR_DEFAULT = "data/dashboards"


def _check_embed_token(token: str) -> EmbedToken:
    et = verify_token(token)
    if et is None:
        raise HTTPException(401, "Token d'embed invalide ou expiré.")
    return et


# ── Token management ──────────────────────────────────────────────────────────

class TokenRequest(BaseModel):
    dashboard_id: str = "*"
    ttl_seconds: int = 3600
    scopes: list[str] = ["read"]


@router.post("/embed/tokens")
def create_embed_token(req: TokenRequest, _: str = Depends(_ADMIN)):
    try:
        et = generate_token(
            dashboard_id=req.dashboard_id,
            ttl_seconds=req.ttl_seconds,
            scopes=req.scopes,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {
        "token": et.token,
        "dashboard_id": et.dashboard_id,
        "expires_at": et.expires_at,
        "scopes": et.scopes,
    }


# ── Embed routes (token-authenticated, CORS-open) ─────────────────────────────

@router.get("/embed/dashboard/{dashboard_id}")
def embed_dashboard(
    dashboard_id: str,
    token: str = Query(...),
    request: Request = None,
):
    et = _check_embed_token(token)
    if et.dashboard_id != "*" and et.dashboard_id != dashboard_id:
        raise HTTPException(403, "Token non autorisé pour ce dashboard.")

    from pathlib import Path
    path = Path(DASHBOARDS_DIR_DEFAULT) / f"{dashboard_id}.yaml"
    if not path.exists():
        raise HTTPException(404, f"Dashboard introuvable : {dashboard_id!r}")

    try:
        dash = load_dashboard(path)
    except Exception as e:
        raise HTTPException(500, str(e))

    return {"id": dash.id, "title": dash.title, "tiles": dash.tiles, "theme": dash.theme}


@router.get("/embed/ask")
def embed_ask(
    q: str = Query(...),
    token: str = Query(...),
    request: Request = None,
):
    et = _check_embed_token(token)
    if "read" not in et.scopes:
        raise HTTPException(403, "Scope 'read' requis.")

    store = request.app.state.store
    if not store.tables:
        raise HTTPException(400, "Aucune donnée chargée.")

    get_graph = request.app.state.get_graph
    s = get_graph().invoke({"question": q})
    return {
        "sql": s.get("sql"),
        "columns": s.get("columns", []),
        "rows": s.get("rows", [])[:200],
        "answer": s.get("answer"),
        "error": s.get("error"),
        "confidence": s.get("confidence"),
    }

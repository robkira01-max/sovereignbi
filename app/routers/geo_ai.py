"""GeoAI router — POST /api/v1/geo/ai-query (P-027)."""
from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.security.rbac import RequireRole

router = APIRouter(prefix="/api/v1/geo", tags=["geo-ai"])

_VIEWER = RequireRole("viewer")
_QUESTION_MAX = 500


# ── Schemas ───────────────────────────────────────────────────────────────────

class GeoAIRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=_QUESTION_MAX)
    locale: str = Field(default="fr", pattern=r"^(fr|en|ar|es)$")


class GeoIntentOut(BaseModel):
    analysis: str
    layer_id: str
    params: dict[str, Any]
    reasoning: str


class GeoAIResponse(BaseModel):
    intent: GeoIntentOut | None
    columns: list[str]
    rows: list[list[Any]]
    map_config: dict[str, Any] | None
    prose: str
    error: str | None


# ── LLM factory ───────────────────────────────────────────────────────────────

def _get_llm_fn():
    """Return a complete(system, user) → str callable based on LLM_PROVIDER."""
    provider = os.environ.get("LLM_PROVIDER", "ollama").lower()
    if provider == "kimi":
        from app.llm.kimi_client import KimiClient
        client = KimiClient()
        return client.complete
    else:
        from app.llm.ollama_client import OllamaClient
        client = OllamaClient()
        return client.complete


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/ai-query/health")
def geo_ai_health(_: str = Depends(_VIEWER)) -> dict:
    provider = os.environ.get("LLM_PROVIDER", "ollama").lower()
    return {"status": "ok", "provider": provider}


@router.post("/ai-query", response_model=GeoAIResponse)
def geo_ai_query(
    body: GeoAIRequest,
    _: str = Depends(_VIEWER),
) -> GeoAIResponse:
    from app.geo_catalog.geo_ai import run as geo_ai_run

    try:
        llm_fn = _get_llm_fn()
    except RuntimeError as exc:
        raise HTTPException(503, f"LLM non disponible : {exc}") from exc

    result = geo_ai_run(body.question, llm_fn)

    intent_out: GeoIntentOut | None = None
    if result.intent and result.intent.analysis:
        intent_out = GeoIntentOut(
            analysis=result.intent.analysis,
            layer_id=result.intent.layer_id,
            params=result.intent.params,
            reasoning=result.intent.reasoning,
        )

    return GeoAIResponse(
        intent=intent_out,
        columns=result.columns,
        rows=result.rows,
        map_config=result.map_config,
        prose=result.prose,
        error=result.error,
    )

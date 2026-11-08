"""Spatial analysis API — P-023 MizanGeo."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.security.rbac import RequireRole
from app.geo_catalog.spatial_engine import SUPPORTED_ANALYSES, SpatialEngine

router = APIRouter(prefix="/api/v1/geo/analyze", tags=["geo-spatial"])

_VIEWER = RequireRole("viewer")


class AnalyzeRequest(BaseModel):
    layer_id: str
    analysis: str
    params: dict[str, Any] = {}


# ── GET /api/v1/geo/analyze/types ────────────────────────────────────────────

@router.get("/types")
async def list_analysis_types(_user=Depends(_VIEWER)):
    return JSONResponse({
        "analyses": [
            {"id": k, "description": v}
            for k, v in SUPPORTED_ANALYSES.items()
        ]
    })


# ── POST /api/v1/geo/analyze ─────────────────────────────────────────────────

@router.post("")
async def run_analysis(req: AnalyzeRequest, _user=Depends(_VIEWER)):
    # Validate analysis type early (before loading DuckDB)
    if req.analysis not in SUPPORTED_ANALYSES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown analysis '{req.analysis}'. "
                   f"Supported: {list(SUPPORTED_ANALYSES)}",
        )
    # Validate layer_id is a simple identifier (no path chars)
    import re
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", req.layer_id):
        raise HTTPException(status_code=400, detail="Invalid layer_id format")

    try:
        engine = SpatialEngine()
        results = engine.analyze(req.layer_id, req.analysis, req.params)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Spatial analysis failed: {exc}")

    return JSONResponse({
        "layer_id":  req.layer_id,
        "analysis":  req.analysis,
        "row_count": len(results),
        "results":   results,
    })

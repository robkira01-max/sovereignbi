"""Geospatial layer catalog API — MizanGeo."""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from app.security.rbac import RequireRole
from app.geo_catalog.registry import get_layer, load_catalog, toggle_layer

_VIEWER = RequireRole("viewer")
_EDITOR = RequireRole("editor")

router = APIRouter(prefix="/api/v1/geo/catalog", tags=["geo-catalog"])


def _layer_to_dict(layer) -> dict:
    d = asdict(layer)
    # Flatten warnings to list of dicts (already done by asdict)
    return d


# ── GET /api/v1/geo/catalog ──────────────────────────────────────────────────

@router.get("")
async def list_layers(
    enabled_only: bool = Query(False, description="Return only enabled layers"),
    _user=Depends(_VIEWER),
):
    catalog = load_catalog()
    layers = catalog.layers
    if enabled_only:
        layers = [la for la in layers if la.enabled]
    return JSONResponse({
        "version": catalog.version,
        "count": len(layers),
        "layers": [_layer_to_dict(la) for la in layers],
    })


# ── GET /api/v1/geo/catalog/{layer_id} ──────────────────────────────────────

@router.get("/{layer_id}")
async def get_layer_metadata(
    layer_id: str,
    _user=Depends(_VIEWER),
):
    layer = get_layer(layer_id)
    if layer is None:
        raise HTTPException(status_code=404, detail=f"Layer '{layer_id}' not found in catalog")
    return JSONResponse(_layer_to_dict(layer))


# ── PUT /api/v1/geo/catalog/{layer_id}/toggle ────────────────────────────────

@router.put("/{layer_id}/toggle")
async def toggle_layer_enabled(
    layer_id: str,
    _user=Depends(_EDITOR),
):
    updated = toggle_layer(layer_id)
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Layer '{layer_id}' not found in catalog")
    return JSONResponse({
        "id": updated.id,
        "enabled": updated.enabled,
        "message": f"Layer '{layer_id}' {'enabled' if updated.enabled else 'disabled'}",
    })

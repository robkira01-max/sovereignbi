"""Geo route — serving GeoJSON for Djibouti administrative boundaries.

Levels:
  adm1      — 6 regions (ADM1 shapefile, bundled in frontend)
  adm2      — 6 districts enriched with population/density (data/geo/dj_adm2.geojson)
  quartiers — 11 Djibouti-ville quartiers (data/geo/dj_quartiers.geojson)
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/v1/geo", tags=["geo"])

_REPO_ROOT = Path(__file__).parent.parent.parent

_LEVEL_PATHS: dict[str, Path] = {
    "adm1":      _REPO_ROOT / "frontend" / "src" / "data" / "dji_adm1.geojson",
    "adm2":      _REPO_ROOT / "data" / "geo" / "dj_adm2.geojson",
    "quartiers": _REPO_ROOT / "data" / "geo" / "dj_quartiers.geojson",
}

_VALID_LEVELS = frozenset(_LEVEL_PATHS)


@router.get("/dj/{level}", summary="GeoJSON limites administratives Djibouti")
async def get_dj_geo(level: str) -> JSONResponse:
    """Retourne un FeatureCollection GeoJSON pour le niveau demandé.

    - **adm1** : 6 régions (source GADM v4.1, CC BY 4.0)
    - **adm2** : 6 districts enrichis (population, superficie, densité)
    - **quartiers** : 11 quartiers de Djibouti-ville (OSM, ODbL — délimitations approximatives)
    """
    if level not in _VALID_LEVELS:
        raise HTTPException(
            status_code=404,
            detail=f"Niveau '{level}' inconnu. Valeurs valides : {sorted(_VALID_LEVELS)}",
        )

    path = _LEVEL_PATHS[level]
    if not path.exists():
        raise HTTPException(
            status_code=503,
            detail=(
                f"Fichier GeoJSON pour le niveau '{level}' introuvable. "
                "Exécutez tools/download_dj_geo.py pour télécharger les données."
            ),
        )

    try:
        content = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise HTTPException(status_code=500, detail=f"Erreur lecture GeoJSON : {exc}") from exc

    return JSONResponse(content=content, media_type="application/geo+json")

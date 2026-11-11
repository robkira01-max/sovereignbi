"""Geo route — serving GeoJSON for Djibouti administrative boundaries and urban layers.

Administrative levels:
  adm1              — 6 regions (ADM1 shapefile, bundled in frontend)
  adm2              — 6 districts enriched with population/density
  quartiers         — 11 Djibouti-ville quartiers (OSM, approximate)
  structures_sante  — 65 health facilities with GPS + personnel

CERD Djibouti-ville layers (source: CERD, ~2015, EPSG:32638 converted to WGS84):
  cerd_equipements_scolaires  — 31 schools
  cerd_equipements_sociaux    — 81 socioeconomic facilities
  cerd_secteurs_adressage     — 14 address sectors
  cerd_communes               — 2 communes
  cerd_ilots                  — 4010 city blocks (simplified 2 m, ~2.3 MB)
  cerd_lignes_bus             — 5 bus lines
  cerd_terminus_bus           — 6 bus terminals
  cerd_voirie                 — 1447 road segments (simplified 1 m)
  cerd_ouvrages               — 22 bridges / crossings
  cerd_typologies_urbaines    — 27 urban typology zones
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/v1/geo", tags=["geo"])

_REPO_ROOT = Path(__file__).parent.parent.parent

_CERD = _REPO_ROOT / "data" / "geo" / "cerd"

_LEVEL_PATHS: dict[str, Path] = {
    "adm1":                       _REPO_ROOT / "frontend" / "src" / "data" / "dji_adm1.geojson",
    "adm2":                       _REPO_ROOT / "data" / "geo" / "dj_adm2.geojson",
    "quartiers":                  _REPO_ROOT / "data" / "geo" / "dj_quartiers.geojson",
    "structures_sante":           _REPO_ROOT / "data" / "geo" / "dj_structures_sante.geojson",
    # CERD Djibouti-ville layers
    "cerd_equipements_scolaires": _CERD / "cerd_equipements_scolaires.geojson",
    "cerd_equipements_sociaux":   _CERD / "cerd_equipements_sociaux.geojson",
    "cerd_secteurs_adressage":    _CERD / "cerd_secteurs_adressage.geojson",
    "cerd_communes":              _CERD / "cerd_communes.geojson",
    "cerd_ilots":                 _CERD / "cerd_ilots.geojson",
    "cerd_lignes_bus":            _CERD / "cerd_lignes_bus.geojson",
    "cerd_terminus_bus":          _CERD / "cerd_terminus_bus.geojson",
    "cerd_voirie":                _CERD / "cerd_voirie.geojson",
    "cerd_ouvrages":              _CERD / "cerd_ouvrages.geojson",
    "cerd_typologies_urbaines":   _CERD / "cerd_typologies_urbaines.geojson",
}

_VALID_LEVELS = frozenset(_LEVEL_PATHS)


@router.get("/dj/{level}", summary="GeoJSON limites administratives Djibouti")
async def get_dj_geo(level: str) -> JSONResponse:
    """Retourne un FeatureCollection GeoJSON pour le niveau demandé.

    - **adm1** : 6 régions (source GADM v4.1, CC BY 4.0)
    - **adm2** : 6 districts enrichis (population, superficie, densité)
    - **quartiers** : 11 quartiers de Djibouti-ville (OSM, ODbL — délimitations approximatives)
    - **structures_sante** : 65 structures sanitaires avec GPS et effectifs (Ministère de la Santé 2020)
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

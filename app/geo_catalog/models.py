"""Geospatial layer metadata models."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class LayerWarning:
    fr: str
    en: str


@dataclass
class GeoLayer:
    id: str
    name_fr: str
    name_en: str
    description_fr: str
    description_en: str
    format: str                       # geojson | pmtiles | gpkg
    geometry_type: str                # Point | LineString | Polygon | ...
    source: str
    license: str
    license_url: str
    date_acquired: str
    coverage: str
    feature_count: int
    status: Literal["validated", "draft", "deprecated"]
    warnings: list[LayerWarning]
    api_endpoint: str
    enabled: bool


@dataclass
class GeoCatalog:
    version: str
    layers: list[GeoLayer] = field(default_factory=list)

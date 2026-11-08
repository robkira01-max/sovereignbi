"""Load and manage the geospatial layer catalog from catalog.yaml."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from .models import GeoCatalog, GeoLayer, LayerWarning

_CATALOG_PATH = Path(__file__).parent.parent.parent / "data" / "geo" / "catalog.yaml"


def _parse_warning(raw: dict) -> LayerWarning:
    return LayerWarning(fr=raw.get("fr", ""), en=raw.get("en", ""))


def _parse_layer(raw: dict) -> GeoLayer:
    warnings = [_parse_warning(w) for w in raw.get("warnings", [])]
    return GeoLayer(
        id=raw["id"],
        name_fr=raw["name_fr"],
        name_en=raw["name_en"],
        description_fr=raw["description_fr"],
        description_en=raw["description_en"],
        format=raw.get("format", "geojson"),
        geometry_type=raw.get("geometry_type", "Polygon"),
        source=raw["source"],
        license=raw["license"],
        license_url=raw["license_url"],
        date_acquired=raw["date_acquired"],
        coverage=raw["coverage"],
        feature_count=int(raw.get("feature_count", 0)),
        status=raw.get("status", "draft"),
        warnings=warnings,
        api_endpoint=raw["api_endpoint"],
        enabled=bool(raw.get("enabled", True)),
        file_path=raw.get("file_path"),
        name_column=raw.get("name_column", "name"),
    )


@lru_cache(maxsize=1)
def _load_catalog_cached() -> GeoCatalog:
    raw = yaml.safe_load(_CATALOG_PATH.read_text(encoding="utf-8"))
    layers = [_parse_layer(item) for item in raw.get("layers", [])]
    return GeoCatalog(version=raw.get("version", "1"), layers=layers)


def load_catalog(catalog_path: Path | None = None) -> GeoCatalog:
    """Load catalog from disk. Pass catalog_path to override default (for tests)."""
    if catalog_path is not None:
        raw = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
        layers = [_parse_layer(item) for item in raw.get("layers", [])]
        return GeoCatalog(version=raw.get("version", "1"), layers=layers)
    return _load_catalog_cached()


def get_layer(layer_id: str, catalog_path: Path | None = None) -> GeoLayer | None:
    catalog = load_catalog(catalog_path)
    for layer in catalog.layers:
        if layer.id == layer_id:
            return layer
    return None


def toggle_layer(layer_id: str, catalog_path: Path | None = None) -> GeoLayer | None:
    """Toggle the enabled flag in catalog.yaml and invalidate cache."""
    path = catalog_path or _CATALOG_PATH
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    found = None
    for item in raw.get("layers", []):
        if item["id"] == layer_id:
            item["enabled"] = not item.get("enabled", True)
            found = item
            break
    if found is None:
        return None
    path.write_text(yaml.safe_dump(raw, allow_unicode=True, default_flow_style=False), encoding="utf-8")
    _load_catalog_cached.cache_clear()
    return _parse_layer(found)

"""Guard the documented coverage of the two CERD datasets.

Two datasets must not be confused (see CLAUDE.md, "Reprise" item 5):
  * the topographic survey (cerd_batiments/routes/hydro/rail/sites) covers all
    three communes, centre included;
  * the older CERD layers (voirie, équipements, secteurs, ...) only cover Balbala.

The UI note in DjiboutiVilleMap.tsx and the osm_centre_voirie catalog entry say
exactly this. If new CERD data arrives for the centre, these tests fail on purpose:
update the note, the catalog description and CLAUDE.md together.

Plain json/gzip only (no geospatial dependency). Balbala lies west of lon 43.14;
"centre" is anything east of lon 43.15.
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path

import pytest
import yaml

_GEO = Path(__file__).parent.parent / "data" / "geo"
_CENTRE_LON = 43.15
_BALBALA_MAX_LON = 43.14


def _lons(coords):
    if isinstance(coords, (list, tuple)) and coords and isinstance(coords[0], (int, float)):
        yield coords[0]
    elif isinstance(coords, (list, tuple)):
        for c in coords:
            yield from _lons(c)


def _lon_range(path: Path) -> tuple[float, float]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as f:
        feats = json.load(f)["features"]
    lons = [x for ft in feats for x in _lons(ft["geometry"]["coordinates"])]
    return min(lons), max(lons)


@pytest.mark.parametrize("name", ["cerd_batiments", "cerd_routes", "cerd_hydro", "cerd_rail"])
def test_topographic_survey_covers_the_centre(name):
    lo, hi = _lon_range(_GEO / f"{name}.geojson.gz")
    assert hi > _CENTRE_LON, f"{name} no longer reaches the centre (max lon {hi})"
    if name != "cerd_rail":  # the railway only runs through the centre
        assert lo < _BALBALA_MAX_LON, f"{name} no longer reaches Balbala (min lon {lo})"


@pytest.mark.parametrize(
    "name",
    [
        "cerd_voirie",
        "cerd_equipements_sociaux",
        "cerd_equipements_scolaires",
        "cerd_secteurs_adressage",
        "cerd_typologies_urbaines",
        "cerd_lignes_bus",
        "cerd_terminus_bus",
    ],
)
def test_older_cerd_layers_are_balbala_only(name):
    _, hi = _lon_range(_GEO / "cerd" / f"{name}.geojson")
    assert hi <= _BALBALA_MAX_LON, (
        f"{name} now extends east of lon {_BALBALA_MAX_LON} (max {hi}): "
        "CERD data for the centre arrived — update the map note, catalog and CLAUDE.md"
    )


def test_osm_catalog_entry_states_both_coverages():
    layers = yaml.safe_load((_GEO / "catalog.yaml").read_text(encoding="utf-8"))
    layers = layers["layers"] if isinstance(layers, dict) and "layers" in layers else layers
    osm = next(layer for layer in layers if layer["id"] == "osm_centre_voirie")
    for key in ("description_fr", "description_en"):
        text = osm[key]
        assert "cerd_voirie" in text and "cerd_routes" in text, key

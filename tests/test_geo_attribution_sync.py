"""The frontend attribution map must stay in sync with data/geo/catalog.yaml."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_REPO = Path(__file__).parent.parent
_OUT = _REPO / "mizanbi-client" / "src" / "data" / "geo_attribution.json"

spec = importlib.util.spec_from_file_location(
    "sync_geo_attribution", _REPO / "tools" / "sync_geo_attribution.py"
)
_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_mod)


def test_generated_file_matches_catalog():
    assert _OUT.exists(), "run tools/sync_geo_attribution.py"
    assert json.loads(_OUT.read_text(encoding="utf-8")) == _mod.build_attribution()


def test_every_layer_has_provider_and_license():
    for lid, a in _mod.build_attribution().items():
        assert a["name"].strip() and a["provider"].strip() and a["license"].strip(), lid


def test_known_providers():
    attr = _mod.build_attribution()
    assert attr["admin_quartiers"]["provider"] == "CERD"
    assert attr["cerd_voirie"]["provider"].startswith("CERD")
    assert "OpenStreetMap" in attr["osm_centre_voirie"]["provider"]

"""Sync map attribution from data/geo/catalog.yaml into the frontend.

catalog.yaml is the single source of truth for layer provenance (source,
licence). This script derives a compact attribution map consumed by
mizanbi-client/src/components/GeoSources.tsx so that map footers update
automatically when the catalog changes.

Usage: .venv/bin/python tools/sync_geo_attribution.py [--check]
  --check  exit 1 if the generated file is out of date (used by tests/CI)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

_REPO = Path(__file__).parent.parent
_CATALOG = _REPO / "data" / "geo" / "catalog.yaml"
_OUT = _REPO / "mizanbi-client" / "src" / "data" / "geo_attribution.json"


def _provider(source: str) -> str:
    """First segment of the source string: the producing organisation."""
    head = re.split(r"[,—]", source, maxsplit=1)[0].strip()
    return head or source.strip()


def build_attribution() -> dict[str, dict[str, str]]:
    catalog = yaml.safe_load(_CATALOG.read_text(encoding="utf-8"))
    out: dict[str, dict[str, str]] = {}
    for layer in catalog["layers"]:
        out[layer["id"]] = {
            "name": layer["name_fr"],
            "provider": _provider(layer["source"]),
            "license": layer["license"],
        }
    return dict(sorted(out.items()))


def main() -> int:
    payload = json.dumps(build_attribution(), ensure_ascii=False, indent=2) + "\n"
    if "--check" in sys.argv:
        if not _OUT.exists() or _OUT.read_text(encoding="utf-8") != payload:
            print(f"{_OUT} is out of date — run tools/sync_geo_attribution.py")
            return 1
        print("geo_attribution.json is in sync")
        return 0
    _OUT.write_text(payload, encoding="utf-8")
    print(f"wrote {_OUT} ({len(build_attribution())} layers)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

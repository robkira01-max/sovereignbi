"""Generate a CycloneDX 1.4 SBOM (Software Bill of Materials) from pyproject.toml.

Usage:
    python tools/generate_sbom.py [--output sbom.json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Licence lookup matching THIRD_PARTY.md
_LICENCE_MAP: dict[str, str] = {
    "fastapi": "MIT",
    "uvicorn": "BSD",
    "python-multipart": "Apache-2.0",
    "httpx": "BSD",
    "duckdb": "MIT",
    "pandas": "BSD",
    "openpyxl": "MIT",
    "xlrd": "BSD",
    "psycopg2-binary": "LGPL-3.0",
    "sqlglot": "MIT",
    "langgraph": "MIT",
    "pyyaml": "MIT",
    "qdrant-client": "Apache-2.0",
    "scikit-learn": "BSD",
    "sentence-transformers": "Apache-2.0",
    "streamlit": "Apache-2.0",
    "plotly": "MIT",
    "pytest": "MIT",
    "fpdf2": "MIT",
    "pymysql": "MIT",
    "pymssql": "LGPL-2.1",
    "pypdf": "MIT",
    "python-docx": "MIT",
}

_DEP_RE = re.compile(r'^"?([A-Za-z0-9_\-]+)[>=<!].*"?')


def _parse_deps(pyproject: Path) -> list[tuple[str, str]]:
    """Return list of (name, version_spec) from [project].dependencies."""
    import tomllib  # stdlib 3.11+

    with open(pyproject, "rb") as f:
        data = tomllib.load(f)

    deps: list[tuple[str, str]] = []
    for raw in data.get("project", {}).get("dependencies", []):
        raw = raw.strip().strip('"')
        # Split on first operator
        m = re.match(r"([A-Za-z0-9_\-\[\]]+)\s*([>=<!].*)?$", raw)
        if m:
            name = m.group(1).split("[")[0].lower()  # strip extras
            spec = (m.group(2) or "").strip()
            deps.append((name, spec))
    return deps


def generate_sbom(pyproject_path: Path | None = None) -> dict:
    root = pyproject_path or (Path(__file__).parent.parent / "pyproject.toml")
    deps = _parse_deps(root)

    components = []
    for name, spec in deps:
        lic = _LICENCE_MAP.get(name, "Unknown")
        components.append({
            "type": "library",
            "name": name,
            "version": spec or "unspecified",
            "licenses": [{"license": {"name": lic}}],
        })

    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.4",
        "version": 1,
        "metadata": {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "component": {
                "type": "application",
                "name": "sovereignbi",
                "version": "0.1.0",
            },
        },
        "components": components,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate CycloneDX 1.4 SBOM")
    parser.add_argument("--output", default="sbom.json", help="Output file path")
    args = parser.parse_args()

    sbom = generate_sbom()
    out = Path(args.output)
    out.write_text(json.dumps(sbom, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"SBOM written to {out} ({len(sbom['components'])} components)", file=sys.stderr)


if __name__ == "__main__":
    main()

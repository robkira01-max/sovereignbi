"""Tests SBOM CycloneDX 1.4."""
from pathlib import Path

import pytest

from tools.generate_sbom import generate_sbom

_PERMISSIVE = {"MIT", "Apache-2.0", "BSD", "LGPL-3.0"}


def test_sbom_structure():
    sbom = generate_sbom()
    assert sbom["bomFormat"] == "CycloneDX"
    assert sbom["specVersion"] == "1.4"
    assert sbom["version"] == 1
    assert "metadata" in sbom
    assert "components" in sbom
    assert isinstance(sbom["components"], list)
    assert len(sbom["components"]) > 0


def test_sbom_metadata():
    sbom = generate_sbom()
    meta = sbom["metadata"]
    assert "timestamp" in meta
    assert meta["component"]["name"] == "sovereignbi"
    assert meta["component"]["type"] == "application"


def test_sbom_contains_fastapi():
    sbom = generate_sbom()
    names = {c["name"] for c in sbom["components"]}
    assert "fastapi" in names


def test_sbom_contains_fpdf2():
    sbom = generate_sbom()
    names = {c["name"] for c in sbom["components"]}
    assert "fpdf2" in names


def test_sbom_all_components_have_name_and_version():
    sbom = generate_sbom()
    for comp in sbom["components"]:
        assert "name" in comp
        assert "version" in comp
        assert comp["name"]


def test_sbom_all_have_licenses():
    sbom = generate_sbom()
    for comp in sbom["components"]:
        assert "licenses" in comp
        assert len(comp["licenses"]) > 0


def test_sbom_only_permissive_or_known_licenses():
    sbom = generate_sbom()
    # All known licences in THIRD_PARTY.md should be permissive (LGPL is noted as acceptable)
    for comp in sbom["components"]:
        for lic_entry in comp["licenses"]:
            name = lic_entry["license"]["name"]
            assert name != "Unknown" or comp["name"] in ("pytest",), \
                f"Component {comp['name']} has unknown licence"


def test_sbom_cli_writes_file(tmp_path, monkeypatch):
    import sys
    out = tmp_path / "test_sbom.json"
    monkeypatch.setattr(sys, "argv", ["generate_sbom.py", "--output", str(out)])
    from tools.generate_sbom import main
    main()
    import json
    data = json.loads(out.read_text())
    assert data["bomFormat"] == "CycloneDX"

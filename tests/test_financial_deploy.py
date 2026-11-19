"""P-073 : le dossier rules/ doit être embarqué dans les images, sinon la production n'a aucune formule."""
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("dockerfile", ["Dockerfile", "Dockerfile.prod"])
def test_images_copy_the_rules_directory(dockerfile):
    lines = [x.strip() for x in (ROOT / dockerfile).read_text().splitlines()]
    assert "COPY rules rules" in lines


def test_shipped_formulas_are_present_and_loadable_from_the_default_location(monkeypatch):
    monkeypatch.delenv("SOVEREIGN_FORMULAS_DIR", raising=False)
    from app.financial.registry import load_registry
    assert len(load_registry().codes()) >= 11

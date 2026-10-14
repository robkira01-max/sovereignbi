"""Sector registry — loads sector-specific SemanticModel from YAML files."""
from __future__ import annotations

from pathlib import Path

from app.semantic.model import SemanticModel, load_model

SECTORS_DIR = Path("semantic/sectors")


def list_sectors() -> list[dict]:
    """Return metadata for all available sector YAML files."""
    if not SECTORS_DIR.exists():
        return []
    result = []
    for path in sorted(SECTORS_DIR.glob("*.yaml")):
        try:
            import yaml

            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            result.append(
                {
                    "id": raw.get("sector", path.stem),
                    "label": raw.get("label", path.stem),
                    "description": raw.get("description", ""),
                    "path": str(path),
                }
            )
        except Exception:
            continue
    return result


def load_sector(sector_id: str) -> SemanticModel:
    """Load a SemanticModel from semantic/sectors/{sector_id}.yaml."""
    path = SECTORS_DIR / f"{sector_id}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Secteur introuvable : {sector_id}")
    return load_model(path)


def sector_exists(sector_id: str) -> bool:
    return (SECTORS_DIR / f"{sector_id}.yaml").exists()

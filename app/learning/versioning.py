"""Versioning of semantic/model.yaml: snapshot, list, rollback."""
from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

VERSIONS_DIR = Path("data/semantic_versions/")
MODEL_PATH = Path("semantic/model.yaml")


def _now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def snapshot(
    label: str = "",
    model_path: Path | None = None,
    versions_dir: Path | None = None,
) -> Path:
    """Save a timestamped copy of model.yaml. Returns the destination path."""
    src = model_path or MODEL_PATH
    vdir = versions_dir or VERSIONS_DIR
    vdir.mkdir(parents=True, exist_ok=True)
    suffix = f"_{label}" if label else ""
    dest = vdir / f"model_{_now_tag()}{suffix}.yaml"
    shutil.copy2(src, dest)
    return dest


def list_versions(versions_dir: Path | None = None) -> list[dict]:
    """List available versions with metadata (filename, path, size, label)."""
    vdir = versions_dir or VERSIONS_DIR
    if not vdir.exists():
        return []
    result = []
    for f in sorted(vdir.glob("model_*.yaml")):
        parts = f.stem.split("_", 3)
        label = parts[3] if len(parts) > 3 else ""
        result.append(
            {
                "filename": f.name,
                "path": str(f),
                "size": f.stat().st_size,
                "label": label,
            }
        )
    return result


def rollback(
    version_path: Path | str,
    model_path: Path | None = None,
    versions_dir: Path | None = None,
) -> None:
    """Restore model.yaml from a versioned copy. Snapshots current state first."""
    src = model_path or MODEL_PATH
    vdir = versions_dir or VERSIONS_DIR
    snapshot(label="pre_rollback", model_path=src, versions_dir=vdir)
    version = Path(version_path)
    if not version.is_absolute():
        version = vdir / version.name
    if not version.exists():
        raise FileNotFoundError(f"Version introuvable : {version}")
    shutil.copy2(version, src)

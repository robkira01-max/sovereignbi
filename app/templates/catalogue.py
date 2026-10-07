"""Catalogue de templates : recherche, tags, notes, clone."""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from app.dashboards.models import load_template, save_template, DashboardTemplate

CATALOGUE_PATH = Path("data/template_catalogue.jsonl")
TEMPLATES_DIR = Path("data/dashboards/templates")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class CatalogueEntry:
    template_id: str
    title: str
    description: str
    tags: list[str] = field(default_factory=list)
    rating: float = 0.0
    rating_count: int = 0
    use_count: int = 0
    created_at: str = ""
    updated_at: str = ""


def _load_catalogue(catalogue_path: Path) -> dict[str, CatalogueEntry]:
    entries: dict[str, CatalogueEntry] = {}
    if not catalogue_path.exists():
        return entries
    for line in catalogue_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
            entries[d["template_id"]] = CatalogueEntry(**d)
        except Exception:
            continue
    return entries


def _write_catalogue(entries: dict[str, CatalogueEntry], catalogue_path: Path) -> None:
    catalogue_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(asdict(e)) for e in entries.values()]
    catalogue_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def register_template(
    template_id: str,
    title: str,
    description: str,
    tags: list[str] = (),
    catalogue_path: Path = CATALOGUE_PATH,
) -> CatalogueEntry:
    entries = _load_catalogue(catalogue_path)
    if template_id in entries:
        return entries[template_id]
    entry = CatalogueEntry(
        template_id=template_id,
        title=title,
        description=description,
        tags=list(tags),
        created_at=_now(),
        updated_at=_now(),
    )
    entries[template_id] = entry
    _write_catalogue(entries, catalogue_path)
    return entry


def rate_template(
    template_id: str,
    rating: float,
    catalogue_path: Path = CATALOGUE_PATH,
) -> CatalogueEntry:
    if not (0.0 <= rating <= 5.0):
        raise ValueError(f"La note doit être entre 0 et 5, reçu : {rating}")
    entries = _load_catalogue(catalogue_path)
    if template_id not in entries:
        raise ValueError(f"Template introuvable : {template_id!r}")
    entry = entries[template_id]
    total = entry.rating * entry.rating_count + rating
    entry.rating_count += 1
    entry.rating = round(total / entry.rating_count, 2)
    entry.updated_at = _now()
    entries[template_id] = entry
    _write_catalogue(entries, catalogue_path)
    return entry


def search_templates(
    query: str = "",
    tags: list[str] = (),
    catalogue_path: Path = CATALOGUE_PATH,
) -> list[CatalogueEntry]:
    entries = list(_load_catalogue(catalogue_path).values())
    q = query.lower().strip()
    if q:
        entries = [
            e for e in entries
            if q in e.title.lower() or q in e.description.lower()
        ]
    if tags:
        entries = [e for e in entries if all(t in e.tags for t in tags)]
    entries.sort(key=lambda e: (-e.use_count, -e.rating))
    return entries


def clone_template(
    template_id: str,
    new_title: str,
    catalogue_path: Path = CATALOGUE_PATH,
    templates_dir: Path = TEMPLATES_DIR,
) -> dict:
    entries = _load_catalogue(catalogue_path)
    if template_id not in entries:
        raise ValueError(f"Template introuvable dans le catalogue : {template_id!r}")

    src_path = templates_dir / f"{template_id}.yaml"
    if not src_path.exists():
        raise FileNotFoundError(f"Fichier template introuvable : {src_path}")

    src = load_template(src_path)
    new_id = str(uuid.uuid4())
    cloned = DashboardTemplate(
        id=new_id,
        title=new_title.strip() or src.title,
        description=src.description,
        tiles=src.tiles,
        theme=src.theme,
    )
    save_template(cloned, templates_dir / f"{new_id}.yaml")

    entry = entries[template_id]
    entry.use_count += 1
    entry.updated_at = _now()
    entries[template_id] = entry
    _write_catalogue(entries, catalogue_path)

    register_template(new_id, cloned.title, cloned.description, entry.tags, catalogue_path)

    return {"new_template_id": new_id, "title": cloned.title}


def get_entry(template_id: str, catalogue_path: Path = CATALOGUE_PATH) -> CatalogueEntry | None:
    return _load_catalogue(catalogue_path).get(template_id)


def list_entries(catalogue_path: Path = CATALOGUE_PATH) -> list[CatalogueEntry]:
    return list(_load_catalogue(catalogue_path).values())


def list_tags(catalogue_path: Path = CATALOGUE_PATH) -> list[str]:
    all_tags: set[str] = set()
    for entry in _load_catalogue(catalogue_path).values():
        all_tags.update(entry.tags)
    return sorted(all_tags)

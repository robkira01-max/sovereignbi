"""Convert an ExtractedStructure into a DashboardTemplate with tiles."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.templates.models import DashboardTemplate, DashboardTile

# Max tiles per template
MAX_TILES = 12

# Section title → chart type heuristic
_SECTION_CHART_MAP: dict[str, str] = {
    "démographie": "bar",
    "demographics": "bar",
    "nationalités": "pie",
    "nationalities": "pie",
    "destinations": "pie",
    "transport": "pie",
    "moyens de transport": "pie",
    "vulnérabilités": "table",
    "vulnerabilities": "table",
    "aperçu": "table",
    "overview": "table",
    "arrivées": "line",
    "arrivals": "line",
    "évolution": "line",
    "evolution": "line",
    "répartition": "bar",
    "distribution": "bar",
    "raisons": "bar",
    "reasons": "bar",
    "résumé": "table",
    "summary": "table",
}


def _chart_type_for_section(title: str) -> str:
    lower = title.lower()
    for keyword, chart in _SECTION_CHART_MAP.items():
        if keyword in lower:
            return chart
    return "bar"


def structure_to_template(
    structure,  # ExtractedStructure — avoid circular import
    user_title: str = "",
    sector: str = "",
) -> DashboardTemplate:
    """Convert ExtractedStructure → DashboardTemplate with tiles (max 12)."""
    from ingestion.universal_extractor import ExtractedStructure  # noqa: PLC0415

    assert isinstance(structure, ExtractedStructure)

    template_id = str(uuid.uuid4())
    title = user_title or structure.title or "Template importé"
    now = datetime.now(tz=timezone.utc).isoformat()

    tiles: list[DashboardTile] = []

    # 1. KPI tiles
    for kpi in structure.kpis:
        if len(tiles) >= MAX_TILES:
            break
        label = kpi.label.strip()
        tiles.append(DashboardTile(
            tile_id=str(uuid.uuid4()),
            title=label[:60] or "Indicateur",
            question=f"Quel est le total de {label} ?",
            chart_type="kpi",
            sql_hint="",
        ))

    # 2. Excel columns: numeric → kpi already added via kpis
    #    categorical → bar/pie, date×numeric → line
    if structure.column_names:
        # Sections from _extract_excel contain column info
        for sec in structure.sections:
            if len(tiles) >= MAX_TILES:
                break
            t = sec.title
            content = sec.content
            chart = _chart_type_for_section(t)
            # Detect if it's a temporal evolution
            if "évolution" in t.lower() or "évolution" in content.lower():
                chart = "line"
            tiles.append(DashboardTile(
                tile_id=str(uuid.uuid4()),
                title=t[:60],
                question=content[:200],
                chart_type=chart,
                sql_hint="",
            ))
    else:
        # PDF / image sections
        for sec in structure.sections:
            if len(tiles) >= MAX_TILES:
                break
            chart = _chart_type_for_section(sec.title)
            question = f"Quelle est la {sec.title.lower()} ?" if sec.content else f"Analyser {sec.title}"
            tiles.append(DashboardTile(
                tile_id=str(uuid.uuid4()),
                title=sec.title[:60],
                question=question[:200],
                chart_type=chart,
                sql_hint="",
            ))

    # Ensure at least 1 tile
    if not tiles:
        tiles.append(DashboardTile(
            tile_id=str(uuid.uuid4()),
            title="Vue générale",
            question="Combien y a-t-il de lignes au total ?",
            chart_type="kpi",
        ))

    return DashboardTemplate(
        template_id=template_id,
        title=title,
        description=f"Importé depuis {structure.detected_sector} ({structure.title})",
        sector=sector or structure.detected_sector,
        source_format="manual",
        tiles=tiles[:MAX_TILES],
        tags=[structure.detected_sector],
        created_at=now,
        updated_at=now,
    )

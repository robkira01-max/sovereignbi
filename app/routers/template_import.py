"""Routes: universal template extraction and management."""
from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel

from app.security.rbac import RequireRole
from app.security.sql_guard import SQLGuardError, validate_sql
from app.templates.models import (
    DashboardTemplate,
    DashboardTile,
    list_templates,
    load_template,
    save_template,
)
from app.templates.structure_to_template import structure_to_template

router = APIRouter(prefix="/user-templates", tags=["user-templates"])

_VIEWER = RequireRole("viewer")
_EDITOR = RequireRole("editor")

_SUPPORTED_TYPES = {
    ".pdf", ".png", ".jpg", ".jpeg",
    ".xlsx", ".xls", ".csv",
}

_MIME_TO_EXT: dict[str, str] = {
    "application/pdf": ".pdf",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.ms-excel": ".xls",
    "text/csv": ".csv",
}


class SaveTemplateRequest(BaseModel):
    title: str
    description: str = ""
    sector: str = "général"
    source_format: str = "manual"
    tiles: list[dict[str, Any]]
    tags: list[str] = []


class ApplyResult(BaseModel):
    tile_id: str
    title: str
    question: str
    chart_type: str
    result: Any
    error: str | None = None


@router.post("/extract")
async def extract_template(
    file: UploadFile = File(...),
    _: str = Depends(_EDITOR),
) -> dict[str, Any]:
    """Upload a file (PDF/PNG/JPEG/XLSX/CSV) and extract a template structure."""
    from ingestion.universal_extractor import UniversalExtractor  # noqa: PLC0415

    filename = file.filename or "upload"
    ext = Path(filename).suffix.lower()
    if not ext and file.content_type:
        ext = _MIME_TO_EXT.get(file.content_type, "")
    if ext not in _SUPPORTED_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Format non supporté : {ext!r}. Formats acceptés : {sorted(_SUPPORTED_TYPES)}",
        )

    content = await file.read()
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        extractor = UniversalExtractor()
        structure = extractor.extract(tmp_path, filename)
        suggested = structure_to_template(structure)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return {
        "structure": {
            "title": structure.title,
            "kpis": [{"value": k.value, "label": k.label} for k in structure.kpis],
            "sections": [{"title": s.title, "content": s.content} for s in structure.sections],
            "column_names": structure.column_names,
            "detected_sector": structure.detected_sector,
        },
        "suggested_template": suggested.to_dict(),
    }


@router.post("/save")
def save_template_route(
    req: SaveTemplateRequest,
    _: str = Depends(_EDITOR),
) -> dict[str, Any]:
    """Persist a DashboardTemplate to disk."""
    tiles = [
        DashboardTile(
            tile_id=t.get("tile_id", str(uuid.uuid4())),
            title=t["title"],
            question=t["question"],
            chart_type=t.get("chart_type", "kpi"),
            sql_hint=t.get("sql_hint", ""),
        )
        for t in req.tiles
    ]
    if not tiles:
        raise HTTPException(400, "Au moins une tuile est requise.")
    template = DashboardTemplate(
        template_id=str(uuid.uuid4()),
        title=req.title,
        description=req.description,
        sector=req.sector,
        source_format=req.source_format,
        tiles=tiles,
        tags=req.tags,
    )
    save_template(template)
    return {"template_id": template.template_id, "tiles_count": len(template.tiles)}


@router.get("")
def list_templates_route(_: str = Depends(_VIEWER)) -> list[dict[str, Any]]:
    """List all saved templates."""
    return list_templates()


@router.get("/{template_id}")
def get_template_route(
    template_id: str,
    _: str = Depends(_VIEWER),
) -> dict[str, Any]:
    """Load a saved template by ID."""
    try:
        tmpl = load_template(template_id)
    except KeyError:
        raise HTTPException(404, f"Template introuvable : {template_id}")
    return tmpl.to_dict()


@router.post("/{template_id}/apply")
def apply_template_route(
    template_id: str,
    request: Request,
    _: str = Depends(_VIEWER),
) -> list[dict[str, Any]]:
    """Apply a template to the currently loaded data store."""
    try:
        tmpl = load_template(template_id)
    except KeyError:
        raise HTTPException(404, f"Template introuvable : {template_id}")

    store = request.app.state.store
    tables = sorted(store.tables)
    if not tables:
        raise HTTPException(400, "Aucune donnée chargée. Utilisez /upload d'abord.")

    table = tables[0]
    results: list[dict[str, Any]] = []

    for tile in tmpl.tiles:
        result = None
        error = None
        sql = tile.sql_hint

        if not sql:
            q = tile.question.lower()
            if any(w in q for w in ["total", "combien", "nombre", "count"]):
                sql = f'SELECT COUNT(*) as total FROM "{table}"'
            elif any(w in q for w in ["répartition", "groupe", "par", "distribution", "top"]):
                sql = f'SELECT * FROM "{table}" LIMIT 10'
            else:
                sql = f'SELECT * FROM "{table}" LIMIT 5'

        try:
            sql = validate_sql(sql, set(tables))
            cols, rows = store.execute(sql)
            result = [dict(zip(cols, row)) for row in rows]
        except (SQLGuardError, Exception) as exc:
            error = str(exc)

        results.append({
            "tile_id": tile.tile_id,
            "title": tile.title,
            "question": tile.question,
            "chart_type": tile.chart_type,
            "sql_used": sql,
            "result": result,
            "error": error,
        })

    return results

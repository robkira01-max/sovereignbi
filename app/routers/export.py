"""Routes d'export : Excel et PDF.

Lit le store et le graphe via request.app.state (injecté par main.py).
"""
from __future__ import annotations

import io

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from starlette.responses import StreamingResponse

from app.export.excel import results_to_excel
from app.export.pdf import results_to_pdf
from app.security.rbac import RequireRole

router = APIRouter(tags=["export"])

_VIEWER = RequireRole("viewer")

_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_PDF_MIME = "application/pdf"


class ExportRequest(BaseModel):
    question: str


def _run_query(request: Request, question: str) -> dict:
    store = request.app.state.store
    if not store.tables:
        raise HTTPException(400, "Aucune donnée chargée. Utilisez /upload d'abord.")
    get_graph = request.app.state.get_graph
    s = get_graph().invoke({"question": question})
    if s.get("error"):
        raise HTTPException(422, s["error"])
    return s


@router.post("/export/excel")
def export_excel(
    req: ExportRequest,
    request: Request,
    _: str = Depends(_VIEWER),
):
    s = _run_query(request, req.question)
    data = results_to_excel(s.get("columns", []), s.get("rows", []))
    return StreamingResponse(
        io.BytesIO(data),
        media_type=_XLSX_MIME,
        headers={"Content-Disposition": "attachment; filename=export.xlsx"},
    )


@router.post("/export/pdf")
def export_pdf(
    req: ExportRequest,
    request: Request,
    _: str = Depends(_VIEWER),
):
    s = _run_query(request, req.question)
    data = results_to_pdf(s.get("columns", []), s.get("rows", []))
    return StreamingResponse(
        io.BytesIO(data),
        media_type=_PDF_MIME,
        headers={"Content-Disposition": "attachment; filename=export.pdf"},
    )


class OfflinePdfRequest(BaseModel):
    columns: list[str]
    rows: list[list]
    title: str = "Résultats"


@router.post("/export/pdf-offline")
def export_pdf_offline(
    req: OfflinePdfRequest,
    request: Request,
    _: str = Depends(_VIEWER),
):
    """Export PDF from pre-computed data — no LLM call, works without network.

    Use this endpoint when Kimi/Ollama is unavailable (field use, network outage).
    The caller provides columns and rows directly (e.g. from cache or a previous query).
    """
    data = results_to_pdf(req.columns, req.rows, req.title)
    return StreamingResponse(
        io.BytesIO(data),
        media_type=_PDF_MIME,
        headers={"Content-Disposition": "attachment; filename=export.pdf"},
    )


class CachedExportRequest(BaseModel):
    question: str
    title: str = ""


@router.post("/export/pdf-cached")
def export_pdf_cached(
    req: CachedExportRequest,
    request: Request,
    _: str = Depends(_VIEWER),
):
    """Return PDF from cache if available; 503 if no cache hit (no LLM call).

    Designed for offline/field use: if the question was previously answered and
    cached, return the PDF immediately without network access.
    """
    from fastapi import HTTPException as _HTTPException

    store = request.app.state.store
    cache = getattr(request.app.state, "query_cache", None)
    if cache is None:
        raise _HTTPException(503, "Cache non disponible.")
    table_names = frozenset(store.tables)
    cached = cache.get(req.question, table_names)
    if cached is None:
        raise _HTTPException(
            503,
            "Résultat non disponible hors ligne. "
            "Posez la question d'abord avec une connexion active."
        )
    title = req.title or req.question[:60]
    data = results_to_pdf(cached.get("columns", []), cached.get("rows", []), title)
    return StreamingResponse(
        io.BytesIO(data),
        media_type=_PDF_MIME,
        headers={"Content-Disposition": "attachment; filename=export.pdf"},
    )

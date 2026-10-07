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

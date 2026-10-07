"""REST API v1 — versioned endpoints mirroring core app routes."""
from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile

from app.api.v1.schemas import (
    AskRequest,
    AskResponse,
    ConfidenceDetail,
    HealthResponse,
    UploadResponse,
)
from app.security.rbac import RequireRole

router = APIRouter(prefix="/api/v1", tags=["v1"])

_VIEWER = RequireRole("viewer")


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Statut de l'API",
    description="Retourne le statut du service et la liste des tables chargées.",
)
def health_v1(request: Request) -> HealthResponse:
    store = request.app.state.store
    return HealthResponse(status="ok", tables=sorted(store.tables))


@router.post(
    "/ask",
    response_model=AskResponse,
    summary="Question en langage naturel",
    description=(
        "Traduit une question en SQL via le LLM local (Ollama), "
        "l'exécute sur DuckDB et retourne une réponse structurée avec score de confiance."
    ),
    responses={
        400: {"description": "Aucune donnée chargée"},
        403: {"description": "Clé API insuffisante"},
    },
)
def ask_v1(req: AskRequest, request: Request, _: str = Depends(_VIEWER)) -> AskResponse:
    store = request.app.state.store
    if not store.tables:
        raise HTTPException(400, "Aucune donnée chargée. Utilisez /api/v1/upload d'abord.")
    get_graph = request.app.state.get_graph
    s = get_graph().invoke({"question": req.question, "dry_run": req.dry_run})
    conf = s.get("confidence")
    return AskResponse(
        sql=s.get("sql"),
        columns=s.get("columns", []),
        rows=[list(r) for r in (s.get("rows", [])[:200])],
        answer=s.get("answer"),
        error=s.get("error"),
        attempts=s.get("attempts"),
        confidence=ConfidenceDetail(**conf) if conf else None,
    )


@router.post(
    "/upload",
    response_model=UploadResponse,
    summary="Charger un fichier de données",
    description="Accepte CSV, XLSX ou XLSM et charge les données dans DuckDB.",
    responses={
        400: {"description": "Format non supporté"},
        403: {"description": "Clé API insuffisante"},
    },
)
async def upload_v1(
    request: Request,
    file: UploadFile = File(...),
    _: str = Depends(_VIEWER),
) -> UploadResponse:
    store = request.app.state.store
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".csv", ".xlsx", ".xlsm"}:
        raise HTTPException(400, "Formats acceptés : CSV, XLSX, XLSM")
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / Path(file.filename).name
        p.write_bytes(await file.read())
        tables = store.load_file(p)
    return UploadResponse(tables=tables)

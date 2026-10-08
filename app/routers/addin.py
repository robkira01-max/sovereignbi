"""Add-in Excel — endpoints dédiés au panneau latéral Office.js."""
from __future__ import annotations

import re
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, field_validator

from app.security.rbac import RequireRole

router = APIRouter(prefix="/api/v1/addin", tags=["excel-addin"])

_VIEWER = RequireRole("viewer")
_MAX_ROWS = 10_000
_MAX_COLS = 500


def _safe_name(s: str) -> str:
    name = re.sub(r"\W+", "_", str(s).strip().lower()).strip("_")
    return name if name and not name[0].isdigit() else f"col_{name}"


class SheetData(BaseModel):
    sheet_name: str
    columns: list[str]
    rows: list[list[Any]]
    source: str = "excel-addin"

    @field_validator("columns")
    @classmethod
    def columns_not_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("columns ne peut pas être vide.")
        if len(v) > _MAX_COLS:
            raise ValueError(f"Trop de colonnes ({len(v)} > {_MAX_COLS}).")
        return v

    @field_validator("rows")
    @classmethod
    def rows_limit(cls, v: list[list[Any]]) -> list[list[Any]]:
        if len(v) > _MAX_ROWS:
            raise ValueError(f"Trop de lignes ({len(v)} > {_MAX_ROWS}).")
        return v


class AddinAskRequest(BaseModel):
    question: str
    context_loaded: bool = True

    @field_validator("question")
    @classmethod
    def question_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("La question ne peut pas être vide.")
        return v.strip()


class AddinAskResponse(BaseModel):
    question: str
    sql: str | None
    columns: list[str]
    rows: list[list[Any]]
    answer: str | None
    confidence_grade: str
    error: str | None = None


@router.post("/push-data")
def push_sheet_data(data: SheetData, request: Request, role: str = Depends(_VIEWER)) -> dict:
    """Reçoit les données de la feuille Excel active et les charge en mémoire DuckDB."""
    store = request.app.state.store

    safe_cols = [_safe_name(c) for c in data.columns]
    n_cols = len(safe_cols)

    # Normalize rows to match column count
    normalized = []
    for row in data.rows:
        if len(row) < n_cols:
            row = list(row) + [None] * (n_cols - len(row))
        else:
            row = list(row)[:n_cols]
        normalized.append(row)

    df = pd.DataFrame(normalized, columns=safe_cols)
    table_name = _safe_name(data.sheet_name) or "excel_sheet"
    loaded_name = store.load_dataframe(table_name, df)

    # Invalidate cache if available
    cache = getattr(request.app.state, "query_cache", None)
    if cache is not None:
        cache.invalidate()

    return {
        "table_name": loaded_name,
        "rows": len(df),
        "columns": len(df.columns),
        "source": data.source,
    }


@router.post("/ask", response_model=AddinAskResponse)
def addin_ask(req: AddinAskRequest, request: Request, role: str = Depends(_VIEWER)) -> AddinAskResponse:
    """Répond à une question en langage naturel sur les données chargées."""
    store = request.app.state.store

    if not store.tables:
        return AddinAskResponse(
            question=req.question,
            sql=None,
            columns=[],
            rows=[],
            answer="Aucune donnée chargée. Utilisez le bouton '📤 Envoyer la feuille active' d'abord.",
            confidence_grade="F",
            error="no_data",
        )

    graph = request.app.state.graph if hasattr(request.app.state, "graph") else None

    if graph is None:
        # Fallback: try to get graph from app build function
        try:
            from app.main import get_graph
            graph = get_graph()
        except Exception:
            graph = None

    if graph is None:
        return AddinAskResponse(
            question=req.question,
            sql=None,
            columns=[],
            rows=[],
            answer="Le pipeline LLM n'est pas disponible. Vérifiez qu'Ollama est démarré.",
            confidence_grade="F",
            error="no_llm",
        )

    try:
        state = graph.invoke({"question": req.question, "dry_run": False})
    except Exception as e:
        return AddinAskResponse(
            question=req.question,
            sql=None,
            columns=[],
            rows=[],
            answer=f"Erreur pipeline : {e}",
            confidence_grade="F",
            error=str(e),
        )

    confidence = state.get("confidence") or {}
    grade = confidence.get("grade", "F") if isinstance(confidence, dict) else "F"

    return AddinAskResponse(
        question=req.question,
        sql=state.get("sql"),
        columns=state.get("columns", []),
        rows=state.get("rows", [])[:200],
        answer=state.get("answer"),
        confidence_grade=grade,
        error=state.get("error"),
    )


@router.get("/status")
def addin_status(request: Request, role: str = Depends(_VIEWER)) -> dict:
    """Retourne l'état de l'add-in : données chargées, tables disponibles."""
    store = request.app.state.store
    return {
        "tables": list(store.tables),
        "tables_count": len(store.tables),
        "ready": len(store.tables) > 0,
    }

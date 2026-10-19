"""Chatbot universel — répond aux questions générales ET aux questions sur les données.

Route intelligente :
  - Si des tables sont chargées ET la question ressemble à une requête de données
    → pipeline SQL (generate_sql → validate/execute → answer)
  - Sinon → réponse directe du LLM (questions générales, aide, BI, méthodologie…)

Historique côté client : le client envoie les N derniers échanges dans `history`.
"""
from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field, field_validator

from app.llm import get_llm_client
from app.security.rbac import RequireRole

router = APIRouter(prefix="/api/v1/chatbot", tags=["chatbot"])

_VIEWER = RequireRole("viewer")

# --- heuristique : mots-clés qui signalent une question sur les données --------
_DATA_PATTERNS = re.compile(
    r"\b(combien|total|somme|moyenne|max|min|liste|montrer|afficher|trier|"
    r"top\s*\d|classement|répartition|distribution|tendance|évolution|"
    r"compare|comparer|par\s+\w+|group by|count|sum|avg|show|list|"
    r"how many|how much|what is the total|rank|filter|where)\b",
    re.I,
)

_MAX_HISTORY = 10       # tours conservés
_MAX_QUESTION_LEN = 2_000


class Turn(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., max_length=4_000)


class ChatRequest(BaseModel):
    question: str = Field(..., max_length=_MAX_QUESTION_LEN)
    history: list[Turn] = Field(default_factory=list, max_length=_MAX_HISTORY)
    use_data_pipeline: bool = Field(
        default=True,
        description="False = forcé en mode général, sans tentative SQL",
    )

    @field_validator("question")
    @classmethod
    def _no_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("La question ne peut pas être vide.")
        return v.strip()


class ChatResponse(BaseModel):
    answer: str
    mode: str                          # "data" | "general"
    sql: str | None = None
    columns: list[str] = []
    rows: list[list[Any]] = []
    confidence: dict | None = None
    error: str | None = None


# --- système prompt général ---------------------------------------------------
_GENERAL_SYSTEM = (
    "Tu es l'assistant BI de SovereignBI, un outil d'analyse de données souverain. "
    "Réponds en français, de manière concise et utile. "
    "Tu peux aider sur : l'analyse de données, la BI, le SQL, la statistique, "
    "les fonctionnalités de l'application, ou toute question générale. "
    "Si on te demande d'analyser des données non chargées, suggère d'uploader un fichier d'abord."
)


def _is_data_question(question: str, has_tables: bool) -> bool:
    """True si la question semble concerner les données chargées."""
    if not has_tables:
        return False
    return bool(_DATA_PATTERNS.search(question))


def _build_history_prompt(history: list[Turn]) -> str:
    if not history:
        return ""
    lines = ["Historique de la conversation :"]
    for t in history[-_MAX_HISTORY:]:
        prefix = "Utilisateur" if t.role == "user" else "Assistant"
        lines.append(f"{prefix} : {t.content}")
    return "\n".join(lines) + "\n\n"


@router.post("", response_model=ChatResponse)
def chat(req: ChatRequest, request: Request, _: str = Depends(_VIEWER)) -> ChatResponse:
    store = request.app.state.store
    has_tables = bool(store.tables)

    use_sql = (
        req.use_data_pipeline
        and has_tables
        and _is_data_question(req.question, has_tables)
    )

    if use_sql:
        return _answer_with_data(req, request)
    return _answer_general(req, request)


def _answer_with_data(req: ChatRequest, request: Request) -> ChatResponse:
    """Passe par le pipeline SQL → DuckDB → réponse structurée."""
    get_graph = request.app.state.get_graph
    try:
        s = get_graph().invoke({"question": req.question, "dry_run": False})
        conf = s.get("confidence")
        return ChatResponse(
            answer=s.get("answer") or "",
            mode="data",
            sql=s.get("sql"),
            columns=s.get("columns", []),
            rows=[list(r) for r in (s.get("rows", [])[:200])],
            confidence=conf,
            error=s.get("error"),
        )
    except Exception as exc:
        # repli gracieux vers le mode général si le pipeline échoue
        return _answer_general(req, request, extra_error=str(exc))


def _answer_general(
    req: ChatRequest,
    request: Request,
    extra_error: str | None = None,
) -> ChatResponse:
    """Répond directement avec le LLM sans passer par SQL."""
    llm = get_llm_client()
    store = request.app.state.store

    # Contexte : tables disponibles (si présentes) pour que le LLM puisse orienter
    tables_hint = ""
    if store.tables:
        tables_hint = f"Tables chargées : {', '.join(sorted(store.tables))}.\n"

    history_text = _build_history_prompt(req.history)
    user_msg = f"{tables_hint}{history_text}Question : {req.question}"

    try:
        answer = llm.complete(_GENERAL_SYSTEM, user_msg)
    except Exception as exc:
        answer = f"Désolé, je ne peux pas répondre pour l'instant ({exc})."

    return ChatResponse(
        answer=answer,
        mode="general",
        error=extra_error,
    )

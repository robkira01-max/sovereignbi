"""Pydantic response/request models for REST v1."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    tables: list[str]
    api_version: str = "v1"


class AskRequest(BaseModel):
    question: str = Field(..., description="Question en langage naturel")
    dry_run: bool = Field(default=False, description="Génère le SQL sans l'exécuter")


class ConfidenceDetail(BaseModel):
    score: float
    label: str
    explanation: str


class AskResponse(BaseModel):
    sql: str | None = None
    columns: list[str] = []
    rows: list[list[Any]] = []
    answer: str | None = None
    error: str | None = None
    attempts: int | None = None
    confidence: ConfidenceDetail | None = None


class UploadResponse(BaseModel):
    tables: list[str]


class ErrorResponse(BaseModel):
    detail: str

"""Routes certificat de précision."""
from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Any

from app.accuracy.certificate import issue_certificate, verify_certificate, PrecisionCertificate
from app.security.rbac import RequireRole

router = APIRouter(prefix="/accuracy", tags=["accuracy"])

_VIEWER = RequireRole("viewer")


class CertificateRequest(BaseModel):
    question: str
    sql: str
    columns: list[str] = []
    rows: list[list[Any]] = []
    answer: str | None = None
    error: str | None = None
    confidence: dict | None = None
    ttl_hours: int = 24


class VerifyRequest(BaseModel):
    cert_id: str
    question: str
    sql: str
    answer: str | None
    issued_at: str
    expires_at: str
    overall_score: float
    grade: str
    checks: list[dict]
    signature: str
    valid: bool = True


@router.post("/certify")
def certify(body: CertificateRequest, _: str = Depends(_VIEWER)):
    cert = issue_certificate(
        question=body.question,
        sql=body.sql,
        columns=body.columns,
        rows=body.rows,
        answer=body.answer,
        error=body.error,
        confidence=body.confidence,
        ttl_hours=body.ttl_hours,
    )
    return asdict(cert)


@router.post("/verify")
def verify(body: VerifyRequest, _: str = Depends(_VIEWER)):
    from app.accuracy.certificate import AccuracyCheck
    cert = PrecisionCertificate(
        cert_id=body.cert_id,
        question=body.question,
        sql=body.sql,
        answer=body.answer,
        issued_at=body.issued_at,
        expires_at=body.expires_at,
        overall_score=body.overall_score,
        grade=body.grade,
        checks=[AccuracyCheck(**c) for c in body.checks],
        signature=body.signature,
        valid=body.valid,
    )
    is_valid = verify_certificate(cert)
    return {"valid": is_valid, "cert_id": body.cert_id}

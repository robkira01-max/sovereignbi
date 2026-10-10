"""Certificat de précision — évalue et atteste la qualité d'une réponse SQL."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone, timedelta
from typing import Any


@dataclass
class AccuracyCheck:
    check_id: str
    name: str
    passed: bool
    score: float
    detail: str


@dataclass
class PrecisionCertificate:
    cert_id: str
    question: str
    sql: str
    answer: str | None
    issued_at: str
    expires_at: str
    overall_score: float
    grade: str
    checks: list[AccuracyCheck]
    signature: str
    valid: bool = True


GRADE_THRESHOLDS = [
    (0.90, "A"),
    (0.75, "B"),
    (0.60, "C"),
    (0.40, "D"),
    (0.0, "F"),
]


def _grade(score: float) -> str:
    for threshold, grade in GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return "F"


def _sign(payload: str) -> str:
    secret = os.environ.get("SOVEREIGN_CERT_SECRET", "")
    if not secret:
        app_env = os.environ.get("APP_ENV", "development").lower()
        if app_env == "production":
            raise RuntimeError(
                "SOVEREIGN_CERT_SECRET est obligatoire en production. "
                "Générer : python3 -c \"import secrets; print(secrets.token_hex(32))\""
            )
        secret = "dev-cert-secret"
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _expires(hours: int = 24) -> str:
    return (datetime.now(tz=timezone.utc) + timedelta(hours=hours)).isoformat()


def check_sql_safety(sql: str) -> AccuracyCheck:
    """Verify SQL is SELECT only and doesn't use dangerous functions."""
    normalized = sql.strip().upper()
    dangerous = ["DROP", "DELETE", "INSERT", "UPDATE", "EXEC", "TRUNCATE",
                 "READ_CSV_AUTO", "READ_PARQUET", "GLOB"]
    found = [kw for kw in dangerous if kw in normalized]
    passed = normalized.startswith("SELECT") and not found
    return AccuracyCheck(
        check_id="sql_safety",
        name="Sécurité SQL",
        passed=passed,
        score=1.0 if passed else 0.0,
        detail="SELECT uniquement, pas de DML" if passed else f"Opérations dangereuses : {found}",
    )


def check_sql_has_result(columns: list[str], rows: list) -> AccuracyCheck:
    """Verify SQL produced results."""
    has_result = bool(columns) and rows is not None
    return AccuracyCheck(
        check_id="has_result",
        name="Résultat non vide",
        passed=has_result,
        score=1.0 if has_result else 0.0,
        detail=f"{len(rows)} lignes, {len(columns)} colonnes" if has_result else "Aucun résultat",
    )


def check_answer_references_data(answer: str | None, columns: list[str]) -> AccuracyCheck:
    """Verify the answer text references at least one column name or numeric value."""
    if not answer:
        return AccuracyCheck(
            check_id="answer_grounded",
            name="Réponse ancrée dans les données",
            passed=False,
            score=0.0,
            detail="Réponse vide",
        )
    answer_lower = answer.lower()
    col_refs = sum(1 for c in columns if c.lower() in answer_lower)
    has_numbers = any(ch.isdigit() for ch in answer)
    passed = col_refs > 0 or has_numbers
    score = min(1.0, (col_refs * 0.5 + (0.5 if has_numbers else 0.0)))
    return AccuracyCheck(
        check_id="answer_grounded",
        name="Réponse ancrée dans les données",
        passed=passed,
        score=score,
        detail=f"{col_refs} colonnes référencées, chiffres présents: {has_numbers}",
    )


def check_confidence(confidence: dict | None) -> AccuracyCheck:
    """Assess confidence score from pipeline."""
    if confidence is None:
        return AccuracyCheck(
            check_id="confidence",
            name="Score de confiance",
            passed=False,
            score=0.0,
            detail="Aucun score de confiance disponible",
        )
    score = float(confidence.get("score", 0.0))
    label = confidence.get("label", "unknown")
    passed = score >= 0.5
    return AccuracyCheck(
        check_id="confidence",
        name="Score de confiance",
        passed=passed,
        score=score,
        detail=f"Score: {score:.2f} ({label})",
    )


def check_no_error(error: str | None) -> AccuracyCheck:
    passed = not error
    return AccuracyCheck(
        check_id="no_error",
        name="Absence d'erreur",
        passed=passed,
        score=1.0 if passed else 0.0,
        detail="Aucune erreur d'exécution" if passed else f"Erreur : {error}",
    )


WEIGHTS = {
    "sql_safety": 0.30,
    "has_result": 0.20,
    "answer_grounded": 0.20,
    "confidence": 0.20,
    "no_error": 0.10,
}


def issue_certificate(
    question: str,
    sql: str,
    columns: list[str],
    rows: list[Any],
    answer: str | None,
    error: str | None,
    confidence: dict | None,
    ttl_hours: int = 24,
) -> PrecisionCertificate:
    checks = [
        check_sql_safety(sql),
        check_sql_has_result(columns, rows),
        check_answer_references_data(answer, columns),
        check_confidence(confidence),
        check_no_error(error),
    ]
    overall = sum(WEIGHTS[c.check_id] * c.score for c in checks)
    overall = round(overall, 3)

    cert_id = str(uuid.uuid4())
    issued = _now()
    expires = _expires(ttl_hours)

    payload = json.dumps({
        "cert_id": cert_id,
        "question": question,
        "sql": sql,
        "overall_score": overall,
        "issued_at": issued,
    }, sort_keys=True)
    signature = _sign(payload)

    return PrecisionCertificate(
        cert_id=cert_id,
        question=question,
        sql=sql,
        answer=answer,
        issued_at=issued,
        expires_at=expires,
        overall_score=overall,
        grade=_grade(overall),
        checks=checks,
        signature=signature,
        valid=True,
    )


def verify_certificate(cert: PrecisionCertificate) -> bool:
    """Verify the certificate signature hasn't been tampered with."""
    payload = json.dumps({
        "cert_id": cert.cert_id,
        "question": cert.question,
        "sql": cert.sql,
        "overall_score": cert.overall_score,
        "issued_at": cert.issued_at,
    }, sort_keys=True)
    expected = _sign(payload)
    return hmac.compare_digest(expected, cert.signature)

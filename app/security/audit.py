"""Audit de configuration de sécurité au démarrage."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

import structlog

log = structlog.get_logger()

_DEFAULT_KEYS = {"change_me_admin", "change_me_editor", "change_me_viewer", "", "admin", "secret"}


@dataclass
class SecurityFinding:
    severity: Literal["critical", "high", "medium", "info"]
    code: str
    title: str
    detail: str
    remediation: str


def audit_configuration() -> list[SecurityFinding]:
    findings: list[SecurityFinding] = []

    admin_key = os.environ.get("SOVEREIGN_ADMIN_KEY", "")
    if not admin_key or admin_key in _DEFAULT_KEYS:
        findings.append(SecurityFinding(
            severity="critical",
            code="SEC-001",
            title="Clé admin par défaut ou absente",
            detail=f"SOVEREIGN_ADMIN_KEY={admin_key!r} est une valeur par défaut ou absente.",
            remediation="Définir SOVEREIGN_ADMIN_KEY avec une valeur aléatoire d'au moins 32 caractères.",
        ))

    embed_secret = os.environ.get("SOVEREIGN_EMBED_SECRET", "")
    if not embed_secret:
        findings.append(SecurityFinding(
            severity="critical",
            code="SEC-002",
            title="SOVEREIGN_EMBED_SECRET absent",
            detail="Aucun secret d'embed configuré — les tokens embed ne peuvent pas être signés.",
            remediation="Définir SOVEREIGN_EMBED_SECRET avec une valeur aléatoire d'au moins 32 caractères.",
        ))
    elif len(embed_secret) < 32:
        findings.append(SecurityFinding(
            severity="critical",
            code="SEC-002",
            title="SOVEREIGN_EMBED_SECRET trop court",
            detail=f"SOVEREIGN_EMBED_SECRET fait {len(embed_secret)} caractères (min 32).",
            remediation="Utiliser un secret d'au moins 32 caractères.",
        ))

    rpm_str = os.environ.get("SOVEREIGN_RATE_LIMIT_RPM", "60")
    try:
        rpm = int(rpm_str)
        if rpm > 10000 and os.environ.get("DEBUG", "").lower() not in ("true", "1", "yes"):
            findings.append(SecurityFinding(
                severity="high",
                code="SEC-003",
                title="Rate limit très élevé en production",
                detail=f"SOVEREIGN_RATE_LIMIT_RPM={rpm} — risque de saturation CPU/mémoire.",
                remediation="Réduire à 60–300 rpm en production.",
            ))
    except ValueError:
        pass

    if os.environ.get("DEBUG", "").lower() in ("true", "1", "yes"):
        findings.append(SecurityFinding(
            severity="high",
            code="SEC-004",
            title="Mode DEBUG activé",
            detail="La variable DEBUG est vraie — les stack traces sont exposées dans les réponses.",
            remediation="Désactiver DEBUG en production.",
        ))

    ollama_url = os.environ.get("OLLAMA_BASE_URL", os.environ.get("OLLAMA_URL", ""))
    if ollama_url:
        import re
        public_ip = re.search(r"https?://(?!localhost|127\.|10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)", ollama_url)
        if public_ip:
            findings.append(SecurityFinding(
                severity="medium",
                code="SEC-005",
                title="Ollama exposé sur IP publique",
                detail=f"OLLAMA_BASE_URL={ollama_url!r} pointe vers une adresse potentiellement publique.",
                remediation="Utiliser une adresse interne (localhost, réseau Docker interne).",
            ))

    viewer_key = os.environ.get("SOVEREIGN_VIEWER_KEY", "")
    editor_key = os.environ.get("SOVEREIGN_EDITOR_KEY", "")
    if viewer_key and editor_key and viewer_key == editor_key:
        findings.append(SecurityFinding(
            severity="info",
            code="SEC-006",
            title="Clés viewer et editor identiques",
            detail="SOVEREIGN_VIEWER_KEY == SOVEREIGN_EDITOR_KEY — les rôles ne sont pas distingués.",
            remediation="Utiliser des clés distinctes par rôle.",
        ))

    return findings


def log_audit_results(findings: list[SecurityFinding]) -> None:
    if not findings:
        log.info("security_audit_ok", message="Aucun problème de configuration détecté.")
        return
    for f in findings:
        logger_fn = getattr(log, f.severity if f.severity != "info" else "info")
        logger_fn(
            "security_finding",
            code=f.code,
            title=f.title,
            detail=f.detail,
            remediation=f.remediation,
        )

"""Clés d'environnement « partagées (héritées) » : plafonnées, datées, jamais attribuables (P-083).

- `SOVEREIGN_LEGACY_KEYS_DEADLINE` (AAAA-MM-JJ, inclus) : après cette date, ces clés sont REFUSÉES. En production la date est
  obligatoire et au plus 180 jours dans le futur (pas de « période annoncée » sans échéance codée).
- Lecture seule : en production (APP_ENV=production) une clé héritée vaut « viewer », quel que soit son rôle configuré.
  Hors production c'est désactivé par défaut (compatibilité des tests) ; `SOVEREIGN_LEGACY_KEYS_READ_ONLY=1|0` force.
- Les clés de test connues et les valeurs par défaut sont refusées au démarrage en production.
- Le journal porte `legacy:<rôle>:<empreinte courte>` (jamais la clé, ni un fragment de la clé).
"""
from __future__ import annotations

import hashlib
import hmac
import os
from datetime import date, datetime, timedelta, timezone

ENV_ROLES = ("admin", "editor", "viewer")
KNOWN_TEST_KEYS = frozenset({"test-viewer-key-s6", "test-editor-key-s6", "test-admin-key-sprint3"})
DEFAULT_KEYS = frozenset({"change_me_admin", "change_me_editor", "change_me_viewer", "admin", "secret", "viewer", "editor"})
MAX_DEADLINE_DAYS = 180


class LegacyConfigError(RuntimeError):
    pass


def is_production() -> bool:
    """Toute valeur d'APP_ENV hors développement/test est traitée comme la production (« prod », « Production » inclus)."""
    return os.environ.get("APP_ENV", "development").strip().lower() not in ("development", "dev", "test", "testing", "")


def configured_roles() -> list[str]:
    return [r for r in ENV_ROLES if os.environ.get(f"SOVEREIGN_{r.upper()}_KEY", "")]


def deadline() -> date | None:
    raw = os.environ.get("SOVEREIGN_LEGACY_KEYS_DEADLINE", "").strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        raise LegacyConfigError("SOVEREIGN_LEGACY_KEYS_DEADLINE doit être une date AAAA-MM-JJ.") from None


def expired(today: date | None = None) -> bool:
    try:
        d = deadline()
    except LegacyConfigError:
        return True          # échéance illisible : échec fermé
    return d is not None and (today or datetime.now(tz=timezone.utc).date()) > d


def read_only() -> bool:
    v = os.environ.get("SOVEREIGN_LEGACY_KEYS_READ_ONLY", "").strip().lower()
    if v in ("1", "true", "yes"):
        return True
    if v in ("0", "false", "no"):
        return False
    return is_production()


def fingerprint(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()[:8]


def match_role(raw_key: str) -> str | None:
    """Rôle configuré de la clé héritée, en temps constant (pas de sortie anticipée)."""
    given, found = raw_key.encode(), None
    for role in ENV_ROLES:
        val = os.environ.get(f"SOVEREIGN_{role.upper()}_KEY", "")
        if val and hmac.compare_digest(given, val.encode()) and found is None:
            found = role
    return found


def status() -> dict:
    d = deadline() if not _bad_deadline() else None
    today = datetime.now(tz=timezone.utc).date()
    roles = configured_roles()
    return {"present": bool(roles), "roles": roles, "deadline": d.isoformat() if d else None,
            "days_left": (d - today).days if d else None, "expired": expired() if d else False,
            "read_only": read_only(), "production": is_production()}


def _bad_deadline() -> bool:
    try:
        deadline()
        return False
    except LegacyConfigError:
        return True


def startup_warnings() -> list[str]:
    roles = configured_roles()
    if not roles:
        return []
    s = status()
    msg = (f"Clés d'environnement héritées présentes ({', '.join(roles)}) : non attribuables à une personne. "
           f"Échéance : {s['deadline'] or 'AUCUNE (définir SOVEREIGN_LEGACY_KEYS_DEADLINE)'} ; "
           f"lecture seule : {'oui' if s['read_only'] else 'non'}. Migrez vers des clés personnelles (mzb_…).")
    return [msg]


def enforce_production_config() -> None:
    """Appelé au démarrage. Refuse de démarrer en production avec des clés de test, des valeurs par défaut ou sans échéance."""
    if not is_production():
        return
    if os.environ.get("SOVEREIGN_LEGACY_KEYS_READ_ONLY", "").strip().lower() in ("0", "false", "no"):
        raise LegacyConfigError("SOVEREIGN_LEGACY_KEYS_READ_ONLY=0 est refusé en production.")
    for role in configured_roles():
        val = os.environ.get(f"SOVEREIGN_{role.upper()}_KEY", "")
        if val in KNOWN_TEST_KEYS or val in DEFAULT_KEYS or val.startswith("change_me"):
            raise LegacyConfigError(f"SOVEREIGN_{role.upper()}_KEY est une clé de test ou par défaut : refusée en production.")
    if configured_roles():
        d = deadline()
        today = datetime.now(tz=timezone.utc).date()
        if d is None:
            raise LegacyConfigError("Clés héritées présentes sans SOVEREIGN_LEGACY_KEYS_DEADLINE : échéance obligatoire en production.")
        if d > today + timedelta(days=MAX_DEADLINE_DAYS):
            raise LegacyConfigError(f"SOVEREIGN_LEGACY_KEYS_DEADLINE trop lointaine (maximum {MAX_DEADLINE_DAYS} jours).")

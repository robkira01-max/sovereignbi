"""Abonnements courriel à un bulletin de tableau de bord (P-067).

Données personnelles (adresses) : fichier JSON local, écriture atomique, jamais journalisées.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import tempfile
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

PATH = Path(os.environ.get("SOVEREIGN_SUBSCRIPTIONS_PATH", "data/subscriptions.json"))
FREQUENCIES = ("daily", "weekly", "monthly")
MAX_PER_DASHBOARD = 50
_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]{1,64}@[A-Za-z0-9.\-]{1,190}\.[A-Za-z]{2,24}$")
_ID_RE = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")
_lock = threading.Lock()


class SubscriptionError(ValueError):
    pass


@dataclass
class Subscription:
    id: str
    dashboard_id: str
    email: str
    frequency: str = "weekly"
    hour_utc: int = 7
    weekday: int = 0                 # 0 = lundi (hebdomadaire)
    day_of_month: int = 1            # mensuel, 1-28
    created_by: str = ""
    created_at: str = ""
    last_sent_at: str | None = None
    last_error: str | None = None
    active: bool = True
    unsub_secret: str = field(default_factory=lambda: secrets.token_hex(16), repr=False)


def _secret() -> bytes:
    return os.environ.get("SOVEREIGN_EMBED_SECRET", "") .encode() or b"dev-unsubscribe-secret"


def unsubscribe_token(sub: Subscription) -> str:
    return hmac.new(_secret(), f"{sub.id}:{sub.unsub_secret}".encode(), hashlib.sha256).hexdigest()


def check_unsubscribe_token(sub: Subscription, token: str) -> bool:
    return hmac.compare_digest(unsubscribe_token(sub), token or "")


def validate(dashboard_id: str, email: str, frequency: str, hour_utc: int, weekday: int, day_of_month: int) -> str:
    email = email.strip().lower()
    if not _ID_RE.match(dashboard_id):
        raise SubscriptionError("Identifiant de tableau de bord invalide.")
    if not _EMAIL_RE.match(email) or ".." in email:
        raise SubscriptionError("Adresse courriel invalide.")
    allowed = [d.strip().lower() for d in os.environ.get("SOVEREIGN_SUBSCRIPTION_DOMAINS", "").split(",") if d.strip()]
    if allowed and email.rsplit("@", 1)[1] not in allowed:
        raise SubscriptionError("Domaine du destinataire non autorisé (SOVEREIGN_SUBSCRIPTION_DOMAINS).")
    if frequency not in FREQUENCIES:
        raise SubscriptionError(f"Fréquence inconnue : {frequency} (attendu : {', '.join(FREQUENCIES)}).")
    if not 0 <= hour_utc <= 23 or not 0 <= weekday <= 6 or not 1 <= day_of_month <= 28:
        raise SubscriptionError("Heure (0-23), jour de semaine (0-6) ou jour du mois (1-28) invalide.")
    return email


def _load(path: Path) -> list[Subscription]:
    if not path.exists():
        return []
    try:
        return [Subscription(**d) for d in json.loads(path.read_text(encoding="utf-8"))]
    except (json.JSONDecodeError, TypeError, OSError):
        raise SubscriptionError("Fichier d'abonnements illisible : corrigez-le ou restaurez-le avant de continuer.") from None


def _save(items: list[Subscription], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump([asdict(s) for s in items], f, ensure_ascii=False, indent=1)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def list_all(path: Path | None = None) -> list[Subscription]:
    with _lock:
        return _load(path or PATH)


def add(sub: Subscription, path: Path | None = None) -> Subscription:
    p = path or PATH
    with _lock:
        items = _load(p)
        same = [s for s in items if s.dashboard_id == sub.dashboard_id]
        if any(s.email == sub.email for s in same):
            raise SubscriptionError("Cette adresse est déjà abonnée à ce tableau de bord.")
        if len(same) >= MAX_PER_DASHBOARD:
            raise SubscriptionError(f"Limite de {MAX_PER_DASHBOARD} abonnés par tableau de bord atteinte.")
        items.append(sub)
        _save(items, p)
    return sub


def remove(sub_id: str, path: Path | None = None) -> bool:
    p = path or PATH
    with _lock:
        items = _load(p)
        kept = [s for s in items if s.id != sub_id]
        if len(kept) == len(items):
            return False
        _save(kept, p)
        return True


def update(sub: Subscription, path: Path | None = None) -> None:
    p = path or PATH
    with _lock:
        items = _load(p)
        _save([sub if s.id == sub.id else s for s in items], p)


def get(sub_id: str, path: Path | None = None) -> Subscription | None:
    return next((s for s in list_all(path) if s.id == sub_id), None)


def new_id() -> str:
    return secrets.token_urlsafe(9)


def is_due(sub: Subscription, now: datetime) -> bool:
    """Vrai si l'échéance planifiée la plus récente (<= now) n'a pas encore été servie."""
    if not sub.active:
        return False
    slot = now.replace(minute=0, second=0, microsecond=0, hour=sub.hour_utc)
    if sub.frequency == "daily":
        if slot > now:
            slot -= timedelta(days=1)
    elif sub.frequency == "weekly":
        slot -= timedelta(days=(slot.weekday() - sub.weekday) % 7)
        if slot > now:
            slot -= timedelta(days=7)
    else:
        slot = slot.replace(day=sub.day_of_month)
        if slot > now:
            first = slot.replace(day=1) - timedelta(days=1)
            slot = first.replace(day=sub.day_of_month)
    if sub.last_sent_at is None:
        # Nouvel abonnement : on n'envoie pas une échéance antérieure à sa création.
        created = datetime.fromisoformat(sub.created_at) if sub.created_at else now
        return slot >= created
    return datetime.fromisoformat(sub.last_sent_at) < slot


def now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)

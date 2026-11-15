"""Registre des incidents de sécurité (P-064). Fichier JSONL, 0600. Pas de données personnelles dans les textes."""
from __future__ import annotations

import json
import os
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

PATH = Path(os.environ.get("SOVEREIGN_INCIDENTS_PATH", "data/incidents.jsonl"))
SEVERITIES = ("low", "medium", "high", "critical")
STATUSES = ("open", "contained", "resolved")
_lock = threading.Lock()


class IncidentError(ValueError):
    pass


class RegisterCorruptError(IncidentError):
    pass


@dataclass
class Incident:
    id: str
    detected_at: str
    reported_at: str
    severity: str
    category: str
    description: str
    personal_data_involved: bool
    status: str = "open"
    clients_notified_at: str | None = None
    authority_notified_at: str | None = None
    actions: list[str] = field(default_factory=list)
    resolved_at: str | None = None


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _iso(value: str | None, label: str) -> str | None:
    if value is None:
        return None
    try:
        datetime.fromisoformat(value)
    except ValueError:
        raise IncidentError(f"{label} : date ISO 8601 attendue.") from None
    return value


def _load() -> list[Incident]:
    if not PATH.exists():
        return []
    try:
        return [Incident(**json.loads(l)) for l in PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
    except (json.JSONDecodeError, TypeError):
        raise RegisterCorruptError("Registre des incidents illisible : ne pas l'écraser, le restaurer.") from None


def _save(items: list[Incident]) -> None:
    PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = PATH.with_suffix(".tmp")
    tmp.write_text("".join(json.dumps(asdict(i), ensure_ascii=False) + "\n" for i in items), encoding="utf-8")
    os.chmod(tmp, 0o600)
    os.replace(tmp, PATH)


def open_incident(detected_at: str, severity: str, category: str, description: str, personal_data_involved: bool) -> Incident:
    if severity not in SEVERITIES:
        raise IncidentError(f"Gravité inconnue (attendu : {', '.join(SEVERITIES)}).")
    if not category.strip() or not description.strip():
        raise IncidentError("Catégorie et description obligatoires.")
    inc = Incident(id=uuid.uuid4().hex[:12], detected_at=_iso(detected_at, "detected_at") or _now(), reported_at=_now(),
                   severity=severity, category=category.strip()[:80], description=description.strip()[:2000],
                   personal_data_involved=personal_data_involved)
    with _lock:
        items = _load()
        items.append(inc)
        _save(items)
    return inc


def update_incident(inc_id: str, *, status: str | None = None, action: str | None = None,
                    clients_notified_at: str | None = None, authority_notified_at: str | None = None) -> Incident:
    if status is not None and status not in STATUSES:
        raise IncidentError(f"Statut inconnu (attendu : {', '.join(STATUSES)}).")
    with _lock:
        items = _load()
        inc = next((i for i in items if i.id == inc_id), None)
        if inc is None:
            raise KeyError(inc_id)
        if status:
            inc.status = status
            inc.resolved_at = _now() if status == "resolved" else None
        if action and action.strip():
            inc.actions.append(f"{_now()} — {action.strip()[:500]}")
        if clients_notified_at is not None:
            inc.clients_notified_at = _iso(clients_notified_at, "clients_notified_at")
        if authority_notified_at is not None:
            inc.authority_notified_at = _iso(authority_notified_at, "authority_notified_at")
        _save(items)
    return inc


def list_incidents(status: str | None = None) -> list[Incident]:
    with _lock:
        return [i for i in _load() if status in (None, i.status)]


def overdue_notifications(hours: int = 72) -> list[Incident]:
    """Incidents touchant des données personnelles, sans notification client, ouverts depuis plus de `hours` h."""
    now = datetime.now(tz=timezone.utc)
    out = []
    for i in list_incidents():
        if i.personal_data_involved and not i.clients_notified_at:
            started = datetime.fromisoformat(i.detected_at)
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            if (now - started).total_seconds() > hours * 3600:
                out.append(i)
    return out

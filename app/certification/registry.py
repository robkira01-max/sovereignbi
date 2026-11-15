"""Jeux de données certifiés (P-069) : « validé par <institution> », lié à l'empreinte des données.

Ce que cela atteste, et ce que cela n'atteste pas :
- Un administrateur de ce serveur enregistre qu'une institution (ex. INSTAD) a validé une table à une date,
  avec une référence (décision, courriel, numéro de note). Le serveur **ne vérifie pas l'institution** :
  la valeur de la pastille est celle de la confiance accordée à l'administrateur qui l'a posée.
- L'**empreinte** du contenu (lignes + schéma) est calculée à ce moment. Dès que les données changent,
  la pastille passe à « modifiée depuis la certification » : une certification ne couvre jamais des
  données qu'elle n'a pas vues.
- La signature HMAC (même secret que le certificat de précision) détecte une modification du fichier
  de registre ; elle n'est pas vérifiable par un tiers sans ce secret.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import threading
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.accuracy.certificate import _sign

PATH = Path(os.environ.get("SOVEREIGN_CERTIFICATIONS_PATH", "data/certified_datasets.json"))
_lock = threading.Lock()
_TABLE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")


class CertificationError(ValueError):
    pass


@dataclass
class Certification:
    id: str
    table: str
    certifier: str
    reference: str
    certified_at: str
    valid_until: str | None
    fingerprint: str
    rows: int
    recorded_by: str
    signature: str
    revoked_at: str | None = None
    revoked_reason: str | None = None


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _payload(c: Certification | dict) -> str:
    d = asdict(c) if isinstance(c, Certification) else c
    keys = ("id", "table", "certifier", "reference", "certified_at", "valid_until", "fingerprint", "rows")
    return json.dumps({k: d[k] for k in keys}, sort_keys=True, ensure_ascii=False)


def fingerprint(store, table: str) -> tuple[str, int]:
    """Empreinte indépendante de l'ordre des lignes : (sha256, nombre de lignes). Agrégat seulement, aucune ligne lue.

    Utilise la connexion DuckDB directement, volontairement : l'empreinte porte sur la table entière,
    quel que soit le périmètre de l'appelant, et ne renvoie aucune donnée de ligne.
    """
    if not _TABLE_RE.match(table) or table.lower() not in {t.lower() for t in store.tables}:
        raise CertificationError("Table inconnue.")
    real = next(t for t in store.tables if t.lower() == table.lower())
    schema = store.con.execute(
        "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = ? ORDER BY ordinal_position",
        [real]).fetchall()
    n, h = store.con.execute(f'SELECT count(*), coalesce(sum(hash(t)::HUGEINT), 0) FROM "{real}" t').fetchone()
    digest = hashlib.sha256(f"{n}|{h}|{schema}".encode()).hexdigest()
    return digest, int(n)


def _load() -> list[Certification]:
    if not PATH.exists():
        return []
    try:
        return [Certification(**d) for d in json.loads(PATH.read_text(encoding="utf-8"))]
    except (json.JSONDecodeError, TypeError, OSError):
        raise CertificationError("Registre de certification illisible : ne pas l'écraser, le restaurer.") from None


def _save(items: list[Certification]) -> None:
    PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=PATH.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump([asdict(c) for c in items], f, ensure_ascii=False, indent=1)
    os.chmod(tmp, 0o600)
    os.replace(tmp, PATH)


def certify(store, table: str, certifier: str, reference: str, recorded_by: str, valid_until: str | None = None) -> Certification:
    certifier, reference = certifier.strip(), reference.strip()
    if not certifier or not reference:
        raise CertificationError("Institution et référence de la validation obligatoires.")
    if valid_until is not None:
        try:
            until = datetime.fromisoformat(valid_until)
        except ValueError:
            raise CertificationError("valid_until : date ISO 8601 attendue.") from None
        if until.tzinfo is None:
            until = until.replace(tzinfo=timezone.utc)
        if until <= datetime.now(tz=timezone.utc):
            raise CertificationError("valid_until doit être dans le futur.")
    fp, n = fingerprint(store, table)
    real = next(t for t in store.tables if t.lower() == table.lower())
    c = Certification(id=uuid.uuid4().hex[:12], table=real, certifier=certifier[:120], reference=reference[:300],
                      certified_at=_now(), valid_until=valid_until, fingerprint=fp, rows=n,
                      recorded_by=recorded_by[:64], signature="")
    c.signature = _sign(_payload(c))
    with _lock:
        items = _load()
        items.append(c)          # l'historique est conservé ; la plus récente non révoquée fait foi
        _save(items)
    return c


def revoke(cert_id: str, reason: str) -> Certification:
    if not reason.strip():
        raise CertificationError("Motif de révocation obligatoire.")
    with _lock:
        items = _load()
        c = next((x for x in items if x.id == cert_id), None)
        if c is None:
            raise KeyError(cert_id)
        if c.revoked_at is None:
            c.revoked_at, c.revoked_reason = _now(), reason.strip()[:300]
            _save(items)
    return c


def history(table: str | None = None) -> list[Certification]:
    with _lock:
        return [c for c in _load() if table is None or c.table.lower() == table.lower()]


def status(store, table: str) -> dict:
    """Pastille d'une table : certified | stale | expired | revoked | tampered | none."""
    mine = history(table)
    if not mine:
        return {"table": table, "status": "none"}
    latest = max(mine, key=lambda c: c.certified_at)
    base = {"table": latest.table, "certification_id": latest.id, "certifier": latest.certifier,
            "reference": latest.reference, "certified_at": latest.certified_at, "valid_until": latest.valid_until}
    import hmac
    if not hmac.compare_digest(_sign(_payload(latest)), latest.signature):
        return {**base, "status": "tampered"}
    if latest.revoked_at:
        return {**base, "status": "revoked", "revoked_at": latest.revoked_at, "revoked_reason": latest.revoked_reason}
    if latest.valid_until:
        until = datetime.fromisoformat(latest.valid_until)
        if until.tzinfo is None:
            until = until.replace(tzinfo=timezone.utc)
        if until <= datetime.now(tz=timezone.utc):
            return {**base, "status": "expired"}
    try:
        current, _n = fingerprint(store, latest.table)
    except CertificationError:
        return {**base, "status": "stale", "detail": "table absente de la base chargée"}
    if current != latest.fingerprint:
        return {**base, "status": "stale", "detail": "les données ont changé depuis la certification"}
    return {**base, "status": "certified"}

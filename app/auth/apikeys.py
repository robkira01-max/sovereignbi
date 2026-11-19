"""Clés API personnelles (P-083) : une clé = un propriétaire, empreinte SHA-256 seule en base.

- Format `mzb_` + 32 octets aléatoires (reconnaissable par les outils de détection de secrets). La clé en clair n'est
  renvoyée qu'UNE fois, à la création ; la base ne contient que l'empreinte et un préfixe non secret.
- SHA-256 suffit (clé à haute entropie, pas un mot de passe) ; comparaison en temps constant.
- Le rôle n'est PAS copié dans la clé : il est relu depuis l'utilisateur à chaque requête (rétrogradation, désactivation
  et révocation jouent immédiatement ; aucun cache).
- Seul le propriétaire crée ses clés ; un administrateur peut seulement révoquer (l'attribution ne se perd pas).
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone

from app.auth import security as sec
from app.security.identity import Identity

KEY_PREFIX = "mzb_"
PREFIX_LEN = len(KEY_PREFIX) + 8          # « mzb_ » + 8 caractères : affichage et recherche, non secret
MAX_RAW_LEN = 128
MAX_ACTIVE_PER_USER = 10
MAX_CREATED_PER_DAY = 20
MAX_LISTED = 200
DEFAULT_TTL_DAYS = 90
MAX_TTL_DAYS = 365
LAST_USED_MIN_INTERVAL_S = 60

_DUMMY = hashlib.sha256(b"dummy").hexdigest()

SCHEMA = """
CREATE TABLE IF NOT EXISTS api_keys (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL,
    key_prefix   TEXT    NOT NULL,
    key_hash     TEXT    NOT NULL UNIQUE,
    label        TEXT    NOT NULL DEFAULT '',
    created_at   TEXT    NOT NULL,
    expires_at   TEXT    NOT NULL,
    last_used_at TEXT,
    revoked_at   TEXT,
    revoked_by   INTEGER,
    revoked_reason TEXT
);
CREATE INDEX IF NOT EXISTS idx_api_keys_prefix ON api_keys(key_prefix);
CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id);
"""


class KeyError_(ValueError):
    """Erreur métier de gestion des clés (message affichable)."""


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _iso(d: datetime) -> str:
    return d.isoformat()


def _digest(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _public(row: sqlite3.Row) -> dict:
    d = {k: row[k] for k in ("id", "user_id", "key_prefix", "label", "created_at", "expires_at", "last_used_at",
                             "revoked_at", "revoked_by", "revoked_reason")}
    d["status"] = _status(row)
    return d


def _status(row: sqlite3.Row) -> str:
    if row["revoked_at"]:
        return "revoked"
    return "expired" if datetime.fromisoformat(row["expires_at"]) <= _now() else "active"


def create_key(user_id: int, label: str = "", ttl_days: int = DEFAULT_TTL_DAYS) -> tuple[dict, str]:
    """Crée une clé pour `user_id` (le propriétaire, vérifié par l'appelant). Renvoie (fiche, clé en clair UNE fois)."""
    if not 1 <= ttl_days <= MAX_TTL_DAYS:
        raise KeyError_(f"La durée de vie doit être comprise entre 1 et {MAX_TTL_DAYS} jours.")
    label = label.strip()[:80]
    raw = KEY_PREFIX + secrets.token_urlsafe(32)
    now = _now()
    with closing(sec._conn()) as c, c:
        c.execute("BEGIN IMMEDIATE")
        u = c.execute("SELECT is_active FROM users WHERE id=?", (user_id,)).fetchone()
        if u is None or not u["is_active"]:
            raise KeyError_("Compte introuvable ou désactivé.")
        n = c.execute("SELECT count(*) FROM api_keys WHERE user_id=? AND revoked_at IS NULL AND expires_at > ?",
                      (user_id, _iso(now))).fetchone()[0]
        made = c.execute("SELECT count(*) FROM api_keys WHERE user_id=? AND created_at > ?",
                         (user_id, _iso(now - timedelta(hours=24)))).fetchone()[0]
        if made >= MAX_CREATED_PER_DAY:
            raise KeyError_("Trop de clés créées aujourd'hui : réessayez plus tard.")
        if n >= MAX_ACTIVE_PER_USER:
            raise KeyError_(f"Maximum {MAX_ACTIVE_PER_USER} clés actives par personne : révoquez-en une d'abord.")
        cur = c.execute(
            "INSERT INTO api_keys (user_id, key_prefix, key_hash, label, created_at, expires_at) VALUES (?,?,?,?,?,?)",
            (user_id, raw[:PREFIX_LEN], _digest(raw), label, _iso(now), _iso(now + timedelta(days=ttl_days))))
        row = c.execute("SELECT * FROM api_keys WHERE id=?", (cur.lastrowid,)).fetchone()
        return _public(row), raw


def list_keys(user_id: int | None = None) -> list[dict]:
    with closing(sec._conn()) as c:
        if user_id is None:
            rows = c.execute("SELECT * FROM api_keys ORDER BY id DESC LIMIT 500").fetchall()
        else:
            rows = c.execute("SELECT * FROM api_keys WHERE user_id=? ORDER BY id DESC LIMIT ?", (user_id, MAX_LISTED)).fetchall()
    return [_public(r) for r in rows]


def get_key(key_id: int) -> dict | None:
    with closing(sec._conn()) as c:
        row = c.execute("SELECT * FROM api_keys WHERE id=?", (key_id,)).fetchone()
    return _public(row) if row else None


def revoke_key(key_id: int, by_user_id: int, reason: str = "") -> dict:
    """Révocation immédiate (idempotente). L'appelant a déjà vérifié : propriétaire ou administrateur."""
    with closing(sec._conn()) as c, c:
        c.execute("BEGIN IMMEDIATE")
        row = c.execute("SELECT * FROM api_keys WHERE id=?", (key_id,)).fetchone()
        if row is None:
            raise KeyError_("Clé introuvable.")
        if not row["revoked_at"]:
            c.execute("UPDATE api_keys SET revoked_at=?, revoked_by=?, revoked_reason=? WHERE id=?",
                      (_iso(_now()), by_user_id, reason.strip()[:200], key_id))
        return _public(c.execute("SELECT * FROM api_keys WHERE id=?", (key_id,)).fetchone())


def revoke_all_for_user(user_id: int, reason: str, by_user_id: int | None = None) -> int:
    with closing(sec._conn()) as c, c:
        return c.execute("UPDATE api_keys SET revoked_at=?, revoked_by=?, revoked_reason=? WHERE user_id=? AND revoked_at IS NULL",
                         (_iso(_now()), by_user_id, reason[:200], user_id)).rowcount


def delete_all_for_user(c: sqlite3.Connection, user_id: int) -> int:
    """Effacement d'un compte (P-064) : dans la transaction de l'appelant."""
    return c.execute("DELETE FROM api_keys WHERE user_id=?", (user_id,)).rowcount


def resolve(raw: str) -> Identity | None:
    """Clé personnelle → identité, ou None (inconnue, révoquée, expirée, compte désactivé : même réponse, pas d'indice).

    Aucune mémoire : chaque appel relit la base, donc une révocation ou une rétrogradation joue à la requête suivante."""
    if not raw.startswith(KEY_PREFIX) or len(raw) > MAX_RAW_LEN:
        return None
    digest = _digest(raw)
    with closing(sec._conn()) as c:
        rows = c.execute("SELECT k.*, u.role AS u_role, u.is_active AS u_active FROM api_keys k "
                         "JOIN users u ON u.id = k.user_id WHERE k.key_prefix=?", (raw[:PREFIX_LEN],)).fetchall()
        match = None
        for r in rows:       # pas de sortie anticipée : travail constant par candidat
            if hmac.compare_digest(r["key_hash"], digest) and match is None:
                match = r
        if not rows:
            hmac.compare_digest(_DUMMY, digest)
        if match is None or match["revoked_at"] or not match["u_active"]:
            return None
        if datetime.fromisoformat(match["expires_at"]) <= _now():
            return None
        if match["u_role"] not in sec.VALID_ROLES:
            return None
        _touch(match)
        return Identity("api_key", match["u_role"], user_id=int(match["user_id"]), key_id=int(match["id"]), key_ref=match["key_prefix"])


def _touch(row: sqlite3.Row) -> None:
    """« Dernière utilisation » : au plus une écriture par minute et par clé (pas de verrou d'écriture à chaque requête)."""
    last = row["last_used_at"]
    if last and (_now() - datetime.fromisoformat(last)).total_seconds() < LAST_USED_MIN_INTERVAL_S:
        return
    try:
        with closing(sec._conn()) as c, c:
            c.execute("UPDATE api_keys SET last_used_at=? WHERE id=? AND (last_used_at IS NULL OR last_used_at < ?)",
                      (_iso(_now()), row["id"], _iso(_now() - timedelta(seconds=LAST_USED_MIN_INTERVAL_S))))
    except sqlite3.OperationalError:
        pass        # base occupée : l'horodatage n'est pas critique, l'authentification ne doit pas échouer pour autant


def rotate_key(key_id: int, user_id: int) -> tuple[dict, str]:
    """Rotation atomique : vérifie que l'ancienne clé est ACTIVE et au propriétaire, crée la nouvelle et révoque l'ancienne
    dans une seule transaction (deux rotations concurrentes ne produisent jamais deux nouvelles clés)."""
    raw = KEY_PREFIX + secrets.token_urlsafe(32)
    now = _now()
    with closing(sec._conn()) as c, c:
        c.execute("BEGIN IMMEDIATE")
        old = c.execute("SELECT * FROM api_keys WHERE id=? AND user_id=?", (key_id, user_id)).fetchone()
        if old is None:
            raise KeyError_("Clé introuvable.")
        if _status(old) != "active":
            raise KeyError_("Seule une clé active peut être renouvelée.")
        if c.execute("SELECT count(*) FROM api_keys WHERE user_id=? AND created_at > ?",
                     (user_id, _iso(now - timedelta(hours=24)))).fetchone()[0] >= MAX_CREATED_PER_DAY:
            raise KeyError_("Trop de clés créées aujourd'hui : réessayez plus tard.")
        ttl = max(1, min(MAX_TTL_DAYS, (datetime.fromisoformat(old["expires_at"]) - datetime.fromisoformat(old["created_at"])).days or 1))
        cur = c.execute("INSERT INTO api_keys (user_id, key_prefix, key_hash, label, created_at, expires_at) VALUES (?,?,?,?,?,?)",
                        (user_id, raw[:PREFIX_LEN], _digest(raw), old["label"], _iso(now), _iso(now + timedelta(days=ttl))))
        c.execute("UPDATE api_keys SET revoked_at=?, revoked_by=?, revoked_reason='rotation' WHERE id=?", (_iso(now), user_id, key_id))
        return _public(c.execute("SELECT * FROM api_keys WHERE id=?", (cur.lastrowid,)).fetchone()), raw

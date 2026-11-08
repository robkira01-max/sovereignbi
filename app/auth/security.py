"""Email/password auth — bcrypt + SQLite sessions."""
from __future__ import annotations

import hashlib
import os
import re
import secrets
import sqlite3
import unicodedata
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bcrypt
import structlog

log = structlog.get_logger()

TOKEN_TTL_HOURS = int(os.environ.get("SESSION_TTL_HOURS", "24"))

_BCRYPT_ROUNDS = 12
_BCRYPT_MAX_BYTES = 72
VALID_ROLES = ("viewer", "editor", "admin")

# Same cost as real hashes so "unknown user" and "wrong password" take the same time.
_DUMMY_HASH = bcrypt.hashpw(b"dummy", bcrypt.gensalt(rounds=_BCRYPT_ROUNDS))


def _auth_db_path() -> Path:
    # Docker prod: override with SOVEREIGN_AUTH_DB=/srv/uploads/auth.db
    # Local dev/test: defaults to ./auth.db (always writable)
    return Path(os.environ.get("SOVEREIGN_AUTH_DB", "./auth.db"))


def _conn() -> sqlite3.Connection:
    p = _auth_db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(p))
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    return c


def _hash_token(token: str) -> str:
    # Tokens are 256-bit random, so an unsalted fast hash is sufficient. Only the
    # hash is stored: a leaked database cannot be replayed as live sessions.
    return hashlib.sha256(token.encode()).hexdigest()


def init_auth_db() -> None:
    with _conn() as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                email         TEXT    UNIQUE NOT NULL COLLATE NOCASE,
                password_hash TEXT    NOT NULL,
                is_active     INTEGER NOT NULL DEFAULT 1,
                created_at    TEXT    DEFAULT (datetime('now')),
                role          TEXT    NOT NULL DEFAULT 'viewer'
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token      TEXT    PRIMARY KEY,
                user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                expires_at TEXT    NOT NULL
            );
        """)
        cols = {r["name"] for r in c.execute("PRAGMA table_info(users)")}
        if "role" not in cols:
            # Databases created before per-user roles: every existing account was
            # implicitly admin, so keep that; new accounts default to 'viewer'.
            c.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'admin'")
        # Sessions are stored as 64-char SHA-256 hex; anything else is a legacy
        # plaintext token that must not outlive the migration.
        c.execute("DELETE FROM sessions WHERE length(token) != 64")


class UserExistsError(ValueError):
    pass


class UserNotFoundError(LookupError):
    pass


class LastAdminError(ValueError):
    """Refused: it would leave no active web admin account."""


MIN_PASSWORD_CHARS = 12
_EMAIL_RE = re.compile(r"[^@\s]{1,64}@[^@\s]+\.[^@\s]+")


def normalize_email(email: str) -> str:
    """Canonical form used for storage, lookup and throttling.

    NFKC folds compatibility look-alikes (e.g. the Kelvin sign) before lower-casing, so
    one visible address maps to exactly one account.
    """
    return unicodedata.normalize("NFKC", email).strip().lower()


def validate_email(email: str) -> str:
    """Return the normalised address or raise ValueError."""
    e = normalize_email(email)
    if len(e) > 254 or not _EMAIL_RE.fullmatch(e):
        raise ValueError("Adresse e-mail invalide.")
    # Control, format (zero-width…), surrogate and separator characters enable look-alike accounts.
    if any(unicodedata.category(ch)[0] in "CZ" for ch in e):
        raise ValueError("Adresse e-mail invalide.")
    return e


def validate_password(password: str) -> None:
    """Policy for passwords chosen through the API (not applied to env-seeded admin)."""
    if len(password) < MIN_PASSWORD_CHARS:
        raise ValueError(f"Mot de passe trop court ({MIN_PASSWORD_CHARS} caractères minimum).")
    if len(password.encode()) > _BCRYPT_MAX_BYTES:
        raise ValueError("Mot de passe trop long (72 octets maximum).")


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)).decode()


def create_user(email: str, password: str, role: str = "viewer") -> int:
    """Insert a user and return its id. Raises UserExistsError on a duplicate e-mail."""
    if role not in VALID_ROLES:
        raise ValueError(f"Rôle inconnu : {role!r}")
    if len(password.encode()) > _BCRYPT_MAX_BYTES:
        raise ValueError("Mot de passe trop long (72 octets maximum).")
    h = _hash_password(password)
    try:
        with closing(_conn()) as c, c:
            cur = c.execute(
                "INSERT INTO users (email, password_hash, role) VALUES (?,?,?)",
                (email, h, role),
            )
            return int(cur.lastrowid)
    except sqlite3.IntegrityError as e:
        raise UserExistsError("Un compte existe déjà avec cette adresse.") from e


_USER_COLS = "id, email, role, is_active, created_at"


def _user_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["is_active"] = bool(d["is_active"])
    return d


def list_users() -> list[dict]:
    with closing(_conn()) as c:
        return [_user_dict(r) for r in c.execute(f"SELECT {_USER_COLS} FROM users ORDER BY id")]


def get_user(user_id: int) -> dict | None:
    with closing(_conn()) as c:
        row = c.execute(f"SELECT {_USER_COLS} FROM users WHERE id=?", (user_id,)).fetchone()
    return _user_dict(row) if row else None


def update_user(user_id: int, role: str | None = None, is_active: bool | None = None) -> dict:
    """Change role and/or active flag. Never removes the last active admin.

    Deactivation revokes the user's sessions. The check and the write share one
    BEGIN IMMEDIATE transaction so two concurrent demotions cannot both succeed.
    """
    if role is not None and role not in VALID_ROLES:
        raise ValueError(f"Rôle inconnu : {role!r}")
    with closing(_conn()) as c, c:
        c.execute("BEGIN IMMEDIATE")
        row = c.execute(f"SELECT {_USER_COLS} FROM users WHERE id=?", (user_id,)).fetchone()
        if row is None:
            raise UserNotFoundError(user_id)
        new_role = role if role is not None else row["role"]
        new_active = int(is_active) if is_active is not None else row["is_active"]
        if row["role"] == "admin" and row["is_active"] and (new_role != "admin" or not new_active):
            others = c.execute(
                "SELECT COUNT(*) FROM users WHERE role='admin' AND is_active=1 AND id!=?", (user_id,)
            ).fetchone()[0]
            if others == 0:
                raise LastAdminError("Impossible : ce serait le dernier administrateur actif.")
        c.execute("UPDATE users SET role=?, is_active=? WHERE id=?", (new_role, new_active, user_id))
        if not new_active:
            c.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
        return _user_dict(c.execute(f"SELECT {_USER_COLS} FROM users WHERE id=?", (user_id,)).fetchone())


def set_password(user_id: int, new_password: str, keep_token: str | None = None) -> None:
    """Replace the password and revoke the user's sessions (except `keep_token`'s)."""
    h = _hash_password(new_password)
    keep = _hash_token(keep_token) if keep_token else ""
    with closing(_conn()) as c, c:
        cur = c.execute("UPDATE users SET password_hash=? WHERE id=?", (h, user_id))
        if cur.rowcount == 0:
            raise UserNotFoundError(user_id)
        c.execute("DELETE FROM sessions WHERE user_id=? AND token != ?", (user_id, keep))


def change_own_password(user_id: int, current: str, new: str, keep_token: str | None = None) -> bool:
    """Verify `current` then set `new`. Returns False if `current` is wrong."""
    with closing(_conn()) as c:
        row = c.execute("SELECT password_hash FROM users WHERE id=? AND is_active=1", (user_id,)).fetchone()
    ok = _password_ok(current, row["password_hash"].encode() if row else _DUMMY_HASH)
    if not row or not ok:
        return False
    set_password(user_id, new, keep_token=keep_token)
    return True


def seed_admin() -> None:
    """Create the admin account from env vars if no users exist yet."""
    email = os.environ.get("ADMIN_EMAIL", "")
    password = os.environ.get("ADMIN_PASSWORD", "")
    if not email or not password:
        return
    with _conn() as c:
        has_users = c.execute("SELECT 1 FROM users LIMIT 1").fetchone()
    if not has_users:
        if len(password) < MIN_PASSWORD_CHARS:
            log.warning("seed_admin_weak_password", min_chars=MIN_PASSWORD_CHARS)
        create_user(normalize_email(email), password, role="admin")


def _password_ok(password: str, password_hash: bytes) -> bool:
    # bcrypt >= 5 raises on > 72 bytes; that must not become a 500 that reveals
    # whether the account exists.
    if len(password.encode()) > _BCRYPT_MAX_BYTES:
        bcrypt.checkpw(b"dummy", _DUMMY_HASH)
        return False
    return bcrypt.checkpw(password.encode(), password_hash)


def login_user(email: str, password: str) -> str | None:
    """Verify credentials; return a new session token or None."""
    with _conn() as c:
        row = c.execute(
            "SELECT id, password_hash FROM users WHERE email=? AND is_active=1",
            (normalize_email(email),),
        ).fetchone()
    if not row:
        _password_ok(password, _DUMMY_HASH)
        return None
    if not _password_ok(password, row["password_hash"].encode()):
        return None
    token = secrets.token_urlsafe(32)
    exp = (datetime.now(timezone.utc) + timedelta(hours=TOKEN_TTL_HOURS)).strftime("%Y-%m-%d %H:%M:%S")
    with _conn() as c:
        c.execute("DELETE FROM sessions WHERE datetime(expires_at) <= datetime('now')")
        # Bound to the hash we just verified: a password reset or deactivation that landed
        # between the check and this insert yields no session.
        cur = c.execute(
            "INSERT INTO sessions (token, user_id, expires_at) "
            "SELECT ?, id, ? FROM users WHERE id=? AND password_hash=? AND is_active=1",
            (_hash_token(token), exp, row["id"], row["password_hash"]),
        )
        if cur.rowcount == 0:
            return None
    return token


def verify_session(token: str) -> dict | None:
    """Return user dict {id, email, role} if token is valid and not expired, else None."""
    with _conn() as c:
        row = c.execute(
            """SELECT u.id, u.email, u.role FROM sessions s
               JOIN users u ON u.id = s.user_id
               WHERE s.token = ?
                 AND datetime(s.expires_at) > datetime('now')
                 AND u.is_active = 1""",
            (_hash_token(token),),
        ).fetchone()
    return dict(row) if row else None


def logout_user(token: str) -> None:
    with _conn() as c:
        c.execute("DELETE FROM sessions WHERE token=?", (_hash_token(token),))

"""Email/password auth — bcrypt + SQLite sessions."""
from __future__ import annotations

import hashlib
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bcrypt

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


def create_user(email: str, password: str, role: str = "viewer") -> None:
    if role not in VALID_ROLES:
        raise ValueError(f"Rôle inconnu : {role!r}")
    if len(password.encode()) > _BCRYPT_MAX_BYTES:
        raise ValueError("Mot de passe trop long (72 octets maximum).")
    h = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)).decode()
    with _conn() as c:
        c.execute(
            "INSERT INTO users (email, password_hash, role) VALUES (?,?,?)",
            (email, h, role),
        )


def seed_admin() -> None:
    """Create the admin account from env vars if no users exist yet."""
    email = os.environ.get("ADMIN_EMAIL", "")
    password = os.environ.get("ADMIN_PASSWORD", "")
    if not email or not password:
        return
    with _conn() as c:
        has_users = c.execute("SELECT 1 FROM users LIMIT 1").fetchone()
    if not has_users:
        create_user(email, password, role="admin")


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
            (email,),
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
        c.execute(
            "INSERT INTO sessions (token, user_id, expires_at) VALUES (?,?,?)",
            (_hash_token(token), row["id"], exp),
        )
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

"""Email/password auth — bcrypt + SQLite sessions."""
from __future__ import annotations

import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bcrypt

TOKEN_TTL_HOURS = int(os.environ.get("SESSION_TTL_HOURS", "24"))


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


def init_auth_db() -> None:
    with _conn() as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                email         TEXT    UNIQUE NOT NULL COLLATE NOCASE,
                password_hash TEXT    NOT NULL,
                is_active     INTEGER NOT NULL DEFAULT 1,
                created_at    TEXT    DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token      TEXT    PRIMARY KEY,
                user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                expires_at TEXT    NOT NULL
            );
        """)


def seed_admin() -> None:
    """Create the admin account from env vars if no users exist yet."""
    email = os.environ.get("ADMIN_EMAIL", "")
    password = os.environ.get("ADMIN_PASSWORD", "")
    if not email or not password:
        return
    with _conn() as c:
        if not c.execute("SELECT 1 FROM users LIMIT 1").fetchone():
            h = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()
            c.execute("INSERT INTO users (email, password_hash) VALUES (?,?)", (email, h))


def login_user(email: str, password: str) -> str | None:
    """Verify credentials; return a new session token or None."""
    with _conn() as c:
        row = c.execute(
            "SELECT id, password_hash FROM users WHERE email=? AND is_active=1",
            (email,),
        ).fetchone()
    if not row:
        # constant-time dummy check to avoid user enumeration timing
        bcrypt.checkpw(b"dummy", bcrypt.hashpw(b"dummy", bcrypt.gensalt(4)))
        return None
    if not bcrypt.checkpw(password.encode(), row["password_hash"].encode()):
        return None
    token = secrets.token_urlsafe(32)
    exp = (datetime.now(timezone.utc) + timedelta(hours=TOKEN_TTL_HOURS)).isoformat()
    with _conn() as c:
        c.execute(
            "INSERT INTO sessions (token, user_id, expires_at) VALUES (?,?,?)",
            (token, row["id"], exp),
        )
    return token


def verify_session(token: str) -> dict | None:
    """Return user dict {id, email} if token is valid and not expired, else None."""
    with _conn() as c:
        row = c.execute(
            """SELECT u.id, u.email FROM sessions s
               JOIN users u ON u.id = s.user_id
               WHERE s.token = ?
                 AND s.expires_at > datetime('now')
                 AND u.is_active = 1""",
            (token,),
        ).fetchone()
    return dict(row) if row else None


def logout_user(token: str) -> None:
    with _conn() as c:
        c.execute("DELETE FROM sessions WHERE token=?", (token,))

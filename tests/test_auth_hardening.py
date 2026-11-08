"""Auth hardening: per-user roles, hashed sessions, bcrypt edge cases, lockout, expiry."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.auth import router as auth_router
from app.auth import security as sec

PW = "correct-horse-battery"


@pytest.fixture()
def db(tmp_path, monkeypatch):
    path = tmp_path / "auth.db"
    monkeypatch.setenv("SOVEREIGN_AUTH_DB", str(path))
    auth_router._throttle.reset()
    sec.init_auth_db()
    yield path
    auth_router._throttle.reset()


@pytest.fixture()
def client(db):
    from app.main import app

    with TestClient(app) as c:
        yield c
    app.state.active_sector_id = None
    app.state.active_semantic_text = None


def _login(client, email, password=PW):
    return client.post("/auth/login", json={"email": email, "password": password})


def _bearer(client, email):
    r = _login(client, email)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


# ── roles ────────────────────────────────────────────────────────────────────

def test_new_user_defaults_to_viewer(db):
    sec.create_user("v@example.org", PW)
    token = sec.login_user("v@example.org", PW)
    assert sec.verify_session(token)["role"] == "viewer"


def test_create_user_rejects_unknown_role_and_long_password(db):
    with pytest.raises(ValueError):
        sec.create_user("x@example.org", PW, role="root")
    with pytest.raises(ValueError):
        sec.create_user("y@example.org", "a" * 73)


def test_seed_admin_creates_admin(db, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAIL", "boss@example.org")
    monkeypatch.setenv("ADMIN_PASSWORD", PW)
    sec.seed_admin()
    token = sec.login_user("boss@example.org", PW)
    assert sec.verify_session(token)["role"] == "admin"


def test_legacy_database_migrates_existing_users_to_admin(tmp_path, monkeypatch):
    path = tmp_path / "legacy.db"
    c = sqlite3.connect(path)
    c.executescript("""
        CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL COLLATE NOCASE, password_hash TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1, created_at TEXT);
        CREATE TABLE sessions (token TEXT PRIMARY KEY, user_id INTEGER NOT NULL, expires_at TEXT NOT NULL);
        INSERT INTO users (email, password_hash) VALUES ('old@example.org', 'x');
    """)
    c.commit()
    c.close()
    monkeypatch.setenv("SOVEREIGN_AUTH_DB", str(path))
    sec.init_auth_db()
    sec.init_auth_db()  # idempotent
    row = sqlite3.connect(path).execute("SELECT role FROM users").fetchone()
    assert row[0] == "admin"


def test_bearer_roles_enforced_on_rbac_routes(client):
    sec.create_user("viewer@example.org", PW, "viewer")
    sec.create_user("editor@example.org", PW, "editor")
    sec.create_user("admin@example.org", PW, "admin")
    url = "/semantic/sectors/humanitarian/activate"

    assert client.post(url, headers=_bearer(client, "viewer@example.org")).status_code == 403
    assert client.post(url, headers=_bearer(client, "editor@example.org")).status_code == 200
    assert client.post(url, headers=_bearer(client, "admin@example.org")).status_code == 200
    assert client.get("/semantic/sectors", headers=_bearer(client, "viewer@example.org")).status_code == 200


def test_unknown_role_in_db_is_denied(client, db):
    sec.create_user("odd@example.org", PW, "viewer")
    with sqlite3.connect(db) as c:
        c.execute("UPDATE users SET role='superuser' WHERE email='odd@example.org'")
    r = client.get("/semantic/sectors", headers=_bearer(client, "odd@example.org"))
    assert r.status_code == 403


# ── sessions ─────────────────────────────────────────────────────────────────

def test_session_token_is_stored_hashed(db):
    sec.create_user("s@example.org", PW)
    token = sec.login_user("s@example.org", PW)
    stored = [r[0] for r in sqlite3.connect(db).execute("SELECT token FROM sessions")]
    assert token not in stored
    assert stored == [sec._hash_token(token)]


def test_logout_revokes_session(db):
    sec.create_user("s@example.org", PW)
    token = sec.login_user("s@example.org", PW)
    assert sec.verify_session(token)
    sec.logout_user(token)
    assert sec.verify_session(token) is None


def test_raw_stored_value_is_not_a_valid_token(db):
    sec.create_user("s@example.org", PW)
    sec.login_user("s@example.org", PW)
    stored = sqlite3.connect(db).execute("SELECT token FROM sessions").fetchone()[0]
    assert sec.verify_session(stored) is None


@pytest.mark.parametrize("fmt", ["iso_t", "sqlite"])
def test_expired_session_rejected_even_earlier_same_day(db, fmt):
    """Regression: 'T'-separated ISO timestamps compared as strings stayed valid till midnight."""
    sec.create_user("e@example.org", PW)
    token = sec.login_user("e@example.org", PW)
    past = datetime.now(timezone.utc) - timedelta(minutes=5)
    value = past.isoformat() if fmt == "iso_t" else past.strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect(db) as c:
        c.execute("UPDATE sessions SET expires_at=?", (value,))
    assert sec.verify_session(token) is None


def test_login_purges_expired_sessions(db):
    sec.create_user("p@example.org", PW)
    old = sec.login_user("p@example.org", PW)
    with sqlite3.connect(db) as c:
        c.execute("UPDATE sessions SET expires_at='2000-01-01 00:00:00'")
    sec.login_user("p@example.org", PW)
    assert sec.verify_session(old) is None
    assert sqlite3.connect(db).execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 1


# ── bcrypt edge cases / enumeration ──────────────────────────────────────────

def test_dummy_hash_has_production_cost():
    assert sec._DUMMY_HASH.startswith(b"$2b$12$")


def test_overlong_password_same_response_for_known_and_unknown_user(client):
    sec.create_user("known@example.org", PW)
    long_pw = "é" * 70  # 140 bytes, 70 chars → passes pydantic, exceeds bcrypt limit
    a = _login(client, "known@example.org", long_pw)
    b = _login(client, "unknown@example.org", long_pw)
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json()


def test_login_request_size_limits(client):
    assert _login(client, "a@example.org", "x" * 257).status_code == 422
    assert _login(client, "a" * 250 + "@example.org", PW).status_code == 422


# ── lockout ──────────────────────────────────────────────────────────────────

def test_lockout_applies_across_email_case_variants(client):
    """email is COLLATE NOCASE in the DB, so the lockout key must be case-insensitive."""
    sec.create_user("Victim@Example.org", PW)
    variants = ["victim@example.org", "VICTIM@example.org", "Victim@example.org",
                "vIcTiM@example.org", "victim@EXAMPLE.org"]
    for v in variants:
        assert _login(client, v, "wrong").status_code == 401
    assert _login(client, "victim@example.org", PW).status_code == 429


def test_successful_login_clears_failures(client):
    sec.create_user("ok@example.org", PW)
    for _ in range(3):
        assert _login(client, "ok@example.org", "wrong").status_code == 401
    assert _login(client, "ok@example.org").status_code == 200
    assert auth_router._throttle._attempts == {}


def test_only_failures_leave_state(client):
    sec.create_user("real@example.org", PW)
    assert _login(client, "real@example.org").status_code == 200
    assert auth_router._throttle._attempts == {}
    _login(client, "ghost@example.org")
    assert len(auth_router._throttle._attempts) == 2  # (email, client) and (email)


def test_attacker_cannot_lock_account_for_users_on_other_addresses(db):
    """5 bad guesses from one address lock that address only, not the account for everyone."""
    from app.main import app

    sec.create_user("admin@example.org", PW, "admin")
    xff = lambda ip: {"X-Forwarded-For": ip}  # noqa: E731
    with TestClient(app, client=("10.0.0.1", 5000)) as proxy:  # trusted (private) peer
        for _ in range(5):
            assert proxy.post("/auth/login", json={"email": "admin@example.org", "password": "x"},
                              headers=xff("198.51.100.7")).status_code == 401
        blocked = proxy.post("/auth/login", json={"email": "admin@example.org", "password": PW},
                             headers=xff("198.51.100.7"))
        assert blocked.status_code == 429
        ok = proxy.post("/auth/login", json={"email": "admin@example.org", "password": PW},
                        headers=xff("203.0.113.9"))
        assert ok.status_code == 200


def test_distributed_guessing_hits_the_per_email_ceiling(db):
    from app.main import app

    sec.create_user("admin@example.org", PW, "admin")
    with TestClient(app, client=("10.0.0.1", 5000)) as proxy:
        for i in range(20):
            r = proxy.post("/auth/login", json={"email": "admin@example.org", "password": "x"},
                           headers={"X-Forwarded-For": f"198.51.100.{i + 1}"})
            assert r.status_code == 401
        r = proxy.post("/auth/login", json={"email": "admin@example.org", "password": PW},
                       headers={"X-Forwarded-For": "203.0.113.200"})
        assert r.status_code == 429


# ── throttle unit behaviour ──────────────────────────────────────────────────

def test_throttle_burst_cannot_exceed_limit():
    """Regression: check-then-act let a parallel burst all pass before any failure was recorded."""
    import threading

    t = auth_router.LoginThrottle()
    allowed: list[bool] = []
    gate = threading.Barrier(40)

    def worker():
        gate.wait()
        allowed.append(t.reserve("a@example.org", "198.51.100.7"))

    threads = [threading.Thread(target=worker) for _ in range(40)]
    [x.start() for x in threads]
    [x.join() for x in threads]
    assert sum(allowed) == 5


def test_throttle_window_expiry_and_sweep():
    t = auth_router.LoginThrottle(window=0.05, max_keys=3)
    for i in range(10):
        assert t.reserve(f"u{i}@example.org", "198.51.100.7")
    import time

    time.sleep(0.1)
    assert t.reserve("fresh@example.org", "198.51.100.7")  # triggers the sweep
    assert len(t._attempts) == 2  # only the fresh pair survives
    # entries that aged out no longer count
    assert all(t.reserve(f"u{i}@example.org", "198.51.100.7") for i in range(10))


# ── legacy sessions ──────────────────────────────────────────────────────────

def test_legacy_plaintext_sessions_are_purged_on_init(db):
    sec.create_user("l@example.org", PW)
    live = sec.login_user("l@example.org", PW)
    with sqlite3.connect(db) as c:
        c.execute("INSERT INTO sessions (token, user_id, expires_at) VALUES ('plain-legacy-token', 1, '2999-01-01 00:00:00')")
    sec.init_auth_db()
    tokens = [r[0] for r in sqlite3.connect(db).execute("SELECT token FROM sessions")]
    assert tokens == [sec._hash_token(live)]
    assert sec.verify_session("plain-legacy-token") is None


# ── API key comparison ───────────────────────────────────────────────────────

def test_api_key_roles(monkeypatch):
    from app.security.rbac import get_role_from_key

    monkeypatch.setenv("SOVEREIGN_ADMIN_KEY", "adm-key")
    monkeypatch.setenv("SOVEREIGN_EDITOR_KEY", "edi-key")
    monkeypatch.setenv("SOVEREIGN_VIEWER_KEY", "vie-key")
    assert get_role_from_key("adm-key") == "admin"
    assert get_role_from_key("edi-key") == "editor"
    assert get_role_from_key("vie-key") == "viewer"
    for bad in ("", "adm-ke", "adm-key ", "ADM-KEY", "é" * 10):
        assert get_role_from_key(bad) is None


def test_unset_key_never_matches_empty(monkeypatch):
    from app.security.rbac import get_role_from_key

    monkeypatch.delenv("SOVEREIGN_ADMIN_KEY", raising=False)
    monkeypatch.delenv("SOVEREIGN_EDITOR_KEY", raising=False)
    monkeypatch.delenv("SOVEREIGN_VIEWER_KEY", raising=False)
    assert get_role_from_key("") is None

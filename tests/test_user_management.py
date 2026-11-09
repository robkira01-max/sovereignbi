"""Account management: admin-only user CRUD, last-admin guard, session revocation, self password change."""
from __future__ import annotations

import sqlite3
import threading

import pytest
from fastapi.testclient import TestClient

from app import feedback
from app.auth import router as auth_router
from app.auth import security as sec

PW = "correct-horse-battery"
NEW_PW = "another-long-passphrase"
ADMIN = {"X-Api-Key": "test-admin-key-sprint3"}
EDITOR = {"X-Api-Key": "test-editor-key-s6"}
VIEWER = {"X-Api-Key": "test-viewer-key-s6"}


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("SOVEREIGN_AUTH_DB", str(tmp_path / "auth.db"))
    monkeypatch.setattr(feedback, "AUDIT_PATH", tmp_path / "audit.jsonl")
    auth_router._throttle.reset()
    sec.init_auth_db()
    yield tmp_path / "auth.db"
    auth_router._throttle.reset()


@pytest.fixture()
def client(db):
    from app.main import app

    with TestClient(app) as c:
        yield c
    app.state.active_sector_id = None  # tests activate a global sector; don't leak it
    app.state.active_semantic_text = None


def _login(client, email, password=PW):
    return client.post("/auth/login", json={"email": email, "password": password})


def _bearer(client, email, password=PW):
    r = _login(client, email, password)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def _create(client, email="new@example.org", role=None, headers=ADMIN, password=PW):
    body = {"email": email, "password": password}
    if role:
        body["role"] = role
    return client.post("/auth/users", json=body, headers=headers)


def _audit_text(db):
    p = db.parent / "audit.jsonl"
    return p.read_text() if p.exists() else ""


# ── authorization ────────────────────────────────────────────────────────────

ENDPOINTS = [
    ("get", "/auth/users", None),
    ("post", "/auth/users", {"email": "x@example.org", "password": PW}),
    ("patch", "/auth/users/1", {"role": "viewer"}),
    ("put", "/auth/users/1/password", {"password": NEW_PW}),
]


@pytest.mark.parametrize("method,path,body", ENDPOINTS)
def test_anonymous_rejected(client, method, path, body):
    assert client.request(method.upper(), path, json=body).status_code == 401


@pytest.mark.parametrize("headers", [VIEWER, EDITOR])
@pytest.mark.parametrize("method,path,body", ENDPOINTS)
def test_non_admin_api_keys_forbidden(client, method, path, body, headers):
    assert client.request(method.upper(), path, json=body, headers=headers).status_code == 403


@pytest.mark.parametrize("role", ["viewer", "editor"])
def test_non_admin_web_users_forbidden(client, role):
    sec.create_user("u@example.org", PW, role)
    h = _bearer(client, "u@example.org")
    assert client.get("/auth/users", headers=h).status_code == 403
    assert _create(client, headers=h).status_code == 403


def test_admin_web_user_allowed(client):
    sec.create_user("boss@example.org", PW, "admin")
    h = _bearer(client, "boss@example.org")
    assert client.get("/auth/users", headers=h).status_code == 200
    assert _create(client, headers=h).status_code == 201


# ── create / list ────────────────────────────────────────────────────────────

def test_create_defaults_to_viewer_and_can_login(client):
    r = _create(client, "  New.User@Example.ORG ")
    assert r.status_code == 201
    u = r.json()
    assert u["email"] == "new.user@example.org"
    assert u["role"] == "viewer" and u["is_active"] is True
    assert set(u) == {"id", "email", "role", "is_active", "created_at"}
    assert r.headers["cache-control"] == "no-store"
    assert _login(client, "new.user@example.org").status_code == 200


def test_created_role_is_enforced(client):
    _create(client, "e@example.org", "editor")
    _create(client, "v@example.org", "viewer")
    url = "/semantic/sectors/humanitarian/activate"
    assert client.post(url, headers=_bearer(client, "v@example.org")).status_code == 403
    assert client.post(url, headers=_bearer(client, "e@example.org")).status_code == 200


def test_duplicate_email_is_409_case_insensitive(client):
    assert _create(client, "dup@example.org").status_code == 201
    assert _create(client, "DUP@example.org").status_code == 409


@pytest.mark.parametrize("email", ["", "no-at-sign", "a@b", "a b@example.org", "@example.org", "a@@example.org"])
def test_invalid_email_rejected(client, email):
    assert _create(client, email).status_code == 422


@pytest.mark.parametrize("pw", ["short", "11-chars-ok", "é" * 40])  # last: 80 bytes
def test_password_policy_enforced_on_create(client, pw):
    r = _create(client, password=pw)
    assert r.status_code == 422
    assert pw not in r.text


def test_invalid_role_rejected(client):
    assert _create(client, role="root").status_code == 422
    assert _create(client, role="superadmin").status_code == 422


def test_list_never_exposes_secrets(client):
    _create(client, "a@example.org")
    body = client.get("/auth/users", headers=ADMIN)
    assert body.status_code == 200
    assert "password" not in body.text.lower() and "$2b$" not in body.text
    assert [u["email"] for u in body.json()] == ["a@example.org"]


# ── update ───────────────────────────────────────────────────────────────────

def test_role_change_takes_effect_for_existing_session(client):
    uid = _create(client, "v@example.org", "viewer").json()["id"]
    h = _bearer(client, "v@example.org")
    url = "/semantic/sectors/humanitarian/activate"
    assert client.post(url, headers=h).status_code == 403
    assert client.patch(f"/auth/users/{uid}", json={"role": "editor"}, headers=ADMIN).json()["role"] == "editor"
    assert client.post(url, headers=h).status_code == 200
    client.patch(f"/auth/users/{uid}", json={"role": "viewer"}, headers=ADMIN)
    assert client.post(url, headers=h).status_code == 403


def test_deactivation_revokes_sessions_and_blocks_login(client):
    uid = _create(client, "gone@example.org").json()["id"]
    h = _bearer(client, "gone@example.org")
    assert client.get("/auth/me", headers=h).status_code == 200
    r = client.patch(f"/auth/users/{uid}", json={"is_active": False}, headers=ADMIN)
    assert r.json()["is_active"] is False
    assert client.get("/auth/me", headers=h).status_code == 401
    assert _login(client, "gone@example.org").status_code == 401
    with sqlite3.connect(sec._auth_db_path()) as c:
        assert c.execute("SELECT COUNT(*) FROM sessions WHERE user_id=?", (uid,)).fetchone()[0] == 0
    client.patch(f"/auth/users/{uid}", json={"is_active": True}, headers=ADMIN)
    assert _login(client, "gone@example.org").status_code == 200


def test_update_validation_and_not_found(client):
    uid = _create(client).json()["id"]
    assert client.patch(f"/auth/users/{uid}", json={}, headers=ADMIN).status_code == 422
    assert client.patch(f"/auth/users/{uid}", json={"role": "root"}, headers=ADMIN).status_code == 422
    assert client.patch("/auth/users/9999", json={"role": "viewer"}, headers=ADMIN).status_code == 404
    assert client.put("/auth/users/9999/password", json={"password": NEW_PW}, headers=ADMIN).status_code == 404


# ── last-admin guard ─────────────────────────────────────────────────────────

def test_cannot_demote_or_deactivate_last_admin(client):
    uid = _create(client, "only@example.org", "admin").json()["id"]
    assert client.patch(f"/auth/users/{uid}", json={"role": "viewer"}, headers=ADMIN).status_code == 409
    assert client.patch(f"/auth/users/{uid}", json={"is_active": False}, headers=ADMIN).status_code == 409
    assert sec.get_user(uid)["role"] == "admin" and sec.get_user(uid)["is_active"]


def test_inactive_admins_do_not_count(client):
    a = _create(client, "a@example.org", "admin").json()["id"]
    b = _create(client, "b@example.org", "admin").json()["id"]
    assert client.patch(f"/auth/users/{b}", json={"is_active": False}, headers=ADMIN).status_code == 200
    assert client.patch(f"/auth/users/{a}", json={"role": "editor"}, headers=ADMIN).status_code == 409


def test_second_admin_allows_demotion(client):
    a = _create(client, "a@example.org", "admin").json()["id"]
    _create(client, "b@example.org", "admin")
    assert client.patch(f"/auth/users/{a}", json={"role": "editor"}, headers=ADMIN).status_code == 200


def test_noop_update_on_last_admin_is_allowed(client):
    uid = _create(client, "only@example.org", "admin").json()["id"]
    assert client.patch(f"/auth/users/{uid}", json={"role": "admin"}, headers=ADMIN).status_code == 200


def test_concurrent_demotions_cannot_remove_every_admin(db):
    a = sec.create_user("a@example.org", PW, "admin")
    b = sec.create_user("b@example.org", PW, "admin")
    gate = threading.Barrier(2)
    results: list[str] = []

    def demote(uid):
        gate.wait()
        try:
            sec.update_user(uid, role="viewer")
            results.append("ok")
        except sec.LastAdminError:
            results.append("refused")

    threads = [threading.Thread(target=demote, args=(u,)) for u in (a, b)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert sorted(results) == ["ok", "refused"]
    assert sum(1 for u in sec.list_users() if u["role"] == "admin" and u["is_active"]) == 1


# ── admin password reset ─────────────────────────────────────────────────────

def test_admin_reset_changes_password_and_revokes_sessions(client):
    uid = _create(client, "u@example.org").json()["id"]
    old = _bearer(client, "u@example.org")
    assert client.put(f"/auth/users/{uid}/password", json={"password": NEW_PW}, headers=ADMIN).status_code == 204
    assert client.get("/auth/me", headers=old).status_code == 401
    assert _login(client, "u@example.org", PW).status_code == 401
    assert _login(client, "u@example.org", NEW_PW).status_code == 200


def test_admin_reset_enforces_policy(client):
    uid = _create(client).json()["id"]
    assert client.put(f"/auth/users/{uid}/password", json={"password": "short"}, headers=ADMIN).status_code == 422
    assert _login(client, "new@example.org", PW).status_code == 200  # unchanged


# ── self-service password change ─────────────────────────────────────────────

def _change(client, headers, current=PW, new=NEW_PW):
    return client.post("/auth/password", json={"current_password": current, "new_password": new}, headers=headers)


def test_change_password_requires_bearer(client):
    assert _change(client, {}).status_code == 401
    assert _change(client, ADMIN).status_code == 401  # API keys have no account to change
    assert _change(client, {"Authorization": "Bearer nope"}).status_code == 401


def test_change_password_success_keeps_current_session_revokes_others(client):
    _create(client, "u@example.org")
    mine, other = _bearer(client, "u@example.org"), _bearer(client, "u@example.org")
    assert _change(client, mine).status_code == 204
    assert client.get("/auth/me", headers=mine).status_code == 200
    assert client.get("/auth/me", headers=other).status_code == 401
    assert _login(client, "u@example.org", PW).status_code == 401
    assert _login(client, "u@example.org", NEW_PW).status_code == 200


def test_change_password_wrong_current_and_policy(client):
    _create(client, "u@example.org")
    h = _bearer(client, "u@example.org")
    assert _change(client, h, current="wrong-current-pw").status_code == 403
    assert _change(client, h, new="short").status_code == 422
    assert _login(client, "u@example.org", PW).status_code == 200  # untouched


def test_change_password_guessing_is_throttled(client):
    _create(client, "u@example.org")
    h = _bearer(client, "u@example.org")
    for _ in range(5):
        assert _change(client, h, current="wrong-current-pw").status_code == 403
    assert _change(client, h).status_code == 429  # even the right password is refused now


# ── audit trail ──────────────────────────────────────────────────────────────

def test_audit_records_events_without_secrets(client, db):
    sec.create_user("boss@example.org", PW, "admin")
    h = _bearer(client, "boss@example.org")
    created = _create(client, "u@example.org", "editor", headers=h).json()
    client.patch(f"/auth/users/{created['id']}", json={"role": "viewer"}, headers=h)
    client.put(f"/auth/users/{created['id']}/password", json={"password": NEW_PW}, headers=ADMIN)
    log = _audit_text(db)
    assert '"user_created"' in log and '"user_updated"' in log and '"user_password_reset"' in log
    assert '"actor": "user:1"' in log and '"actor": "api_key"' in log
    assert PW not in log and NEW_PW not in log and "$2b$" not in log
    assert "u@example.org" not in log
    entries = feedback.load_audit(db.parent / "audit.jsonl")
    assert len(entries) == 3 and all(e.hash for e in entries)


def test_audit_survives_write_failure(client, db, monkeypatch):
    def boom(*a, **k):
        raise OSError("disk full")

    monkeypatch.setattr("app.auth.users_router.record_audit", boom)
    assert _create(client).status_code == 201


# ── data layer ───────────────────────────────────────────────────────────────

def test_create_user_returns_id_and_rejects_duplicates(db):
    uid = sec.create_user("a@example.org", PW)
    assert isinstance(uid, int) and sec.get_user(uid)["email"] == "a@example.org"
    with pytest.raises(sec.UserExistsError):
        sec.create_user("A@EXAMPLE.ORG", PW)


@pytest.mark.parametrize("fn", [sec.update_user, sec.set_password])
def test_missing_user_raises(db, fn):
    with pytest.raises(sec.UserNotFoundError):
        fn(123, "viewer") if fn is sec.update_user else fn(123, NEW_PW)


def test_seed_admin_rejects_short_password(db, monkeypatch):
    # H5 — seed_admin must refuse passwords shorter than MIN_PASSWORD_CHARS
    monkeypatch.setenv("ADMIN_EMAIL", "boss@example.org")
    monkeypatch.setenv("ADMIN_PASSWORD", "short")
    with pytest.raises(ValueError, match="ADMIN_PASSWORD trop court"):
        sec.seed_admin()


# ── CLI ──────────────────────────────────────────────────────────────────────

def _run_cli(monkeypatch, argv, passwords, tty=True):
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location("create_user_cli", Path("tools/create_user.py"))
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    it = iter(passwords)
    monkeypatch.setattr("getpass.getpass", lambda *_: next(it))
    if tty:
        monkeypatch.setattr("sys.stdin", type("Tty", (), {"isatty": staticmethod(lambda: True)})())
    return cli.main(argv)


def test_cli_creates_user(db, monkeypatch, capsys):
    assert _run_cli(monkeypatch, ["Ops@Example.org", "--role", "editor"], [PW, PW]) == 0
    assert "Ops@Example.org" not in capsys.readouterr().out  # normalised
    u = next(u for u in sec.list_users() if u["email"] == "ops@example.org")
    assert u["role"] == "editor"
    assert sec.login_user("ops@example.org", PW)


@pytest.mark.parametrize("passwords,msg", [([PW, "different-password!"], "correspondent"), (["short", "short"], "trop court")])
def test_cli_rejects_bad_passwords(db, monkeypatch, capsys, passwords, msg):
    assert _run_cli(monkeypatch, ["a@example.org"], passwords) == 1
    assert msg in capsys.readouterr().err
    assert sec.list_users() == []


def test_cli_rejects_duplicate_and_bad_email(db, monkeypatch, capsys):
    sec.create_user("a@example.org", PW)
    assert _run_cli(monkeypatch, ["a@example.org"], [PW, PW]) == 1
    assert _run_cli(monkeypatch, ["not-an-email"], []) == 1
    assert len(sec.list_users()) == 1


def test_cli_refuses_non_interactive_stdin(db, monkeypatch, capsys):
    """Without a TTY getpass echoes the password back."""
    assert _run_cli(monkeypatch, ["a@example.org"], [PW, PW], tty=False) == 1
    assert "non interactive" in capsys.readouterr().err
    assert sec.list_users() == []


def test_cli_writes_audit_entry(db, monkeypatch):
    assert _run_cli(monkeypatch, ["ops@example.org", "--role", "admin"], [PW, PW]) == 0
    log = _audit_text(db)
    assert '"user_created"' in log and '"actor": "cli"' in log
    assert PW not in log and "ops@example.org" not in log


# ── review round 2 ───────────────────────────────────────────────────────────

def test_login_attempts_cannot_exhaust_another_users_password_change_budget(client):
    """Regression: the throttle key for password change was a string any login 'email' could equal."""
    uid = _create(client, "victim@example.org").json()["id"]
    h = _bearer(client, "victim@example.org")
    for _ in range(25):
        client.post("/auth/login", json={"email": f"pwchange:{uid}", "password": "x"})
    assert _change(client, h).status_code == 204


def test_throttle_namespaces_are_independent():
    t = auth_router.LoginThrottle(max_per_client=1)
    assert t.reserve("7", "c", ns="login")
    assert not t.reserve("7", "c", ns="login")
    assert t.reserve("7", "c", ns="pwchange")
    t.clear("7", "c", ns="login")
    assert t.reserve("7", "c", ns="login")


def _chain_ok(path):
    import hashlib
    import json

    prev = ""
    for line in path.read_text().splitlines():
        e = json.loads(line)
        h = e.pop("hash")
        body = json.dumps(e, ensure_ascii=False, sort_keys=True)
        if hashlib.sha256((prev + body).encode()).hexdigest() != h:
            return False
        prev = h
    return True


def test_concurrent_audit_writes_keep_the_chain_intact(tmp_path):
    """Regression: unlocked read-last-hash-then-append forked the chain under concurrency."""
    path = tmp_path / "audit.jsonl"
    gate = threading.Barrier(30)

    def work(i):
        gate.wait()
        for j in range(5):
            feedback.record_audit("user_updated", {"actor": f"t{i}", "n": j}, path=path)

    threads = [threading.Thread(target=work, args=(i,)) for i in range(30)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert len(path.read_text().splitlines()) == 150
    assert _chain_ok(path)


def test_locked_database_is_503_not_500(client, monkeypatch):
    def locked(*a, **k):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(sec, "update_user", locked)
    monkeypatch.setattr(sec, "list_users", locked)
    assert client.patch("/auth/users/1", json={"role": "viewer"}, headers=ADMIN).status_code == 503
    assert client.get("/auth/users", headers=ADMIN).status_code == 503


@pytest.mark.parametrize("uid", [0, -1, 2**63, 2**70])
def test_user_id_bounds(client, uid):
    assert client.patch(f"/auth/users/{uid}", json={"role": "viewer"}, headers=ADMIN).status_code == 422
    assert client.put(f"/auth/users/{uid}/password", json={"password": NEW_PW}, headers=ADMIN).status_code == 422


@pytest.mark.parametrize("email", ["a\u200bb@example.org", "a\x00b@example.org", "a\tb@example.org", "ab@exam\u200dple.org",
                                   "a\u2028b@example.org"])
def test_invisible_and_control_characters_rejected_in_email(client, email):
    assert _create(client, email).status_code == 422


def test_email_normalisation_is_consistent_between_create_and_login(client):
    kelvin = "\u212aelvin@example.org"  # KELVIN SIGN: NFKC -> 'K'
    assert _create(client, kelvin).json()["email"] == "kelvin@example.org"
    assert _create(client, "kelvin@example.org").status_code == 409  # same account, no look-alike duplicate
    for typed in (kelvin, "kelvin@example.org", "  Kelvin@Example.ORG "):
        assert _login(client, typed).status_code == 200, typed


def test_lockout_key_uses_the_same_normalisation(client):
    _create(client, "kelvin@example.org")
    for typed in ["\u212aelvin@example.org", "kelvin@example.org", " KELVIN@example.org", "Kelvin@example.org", "kelvin@EXAMPLE.org"]:
        assert _login(client, typed, "wrong-password-x").status_code == 401
    assert _login(client, "kelvin@example.org").status_code == 429


def test_seed_admin_normalises_email(db, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAIL", "  Admin@Example.ORG ")
    monkeypatch.setenv("ADMIN_PASSWORD", PW)
    sec.seed_admin()
    assert [u["email"] for u in sec.list_users()] == ["admin@example.org"]


def test_default_admin_api_key_refused_in_production(client, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SOVEREIGN_ADMIN_KEY", "change_me_admin")
    r = client.get("/auth/users", headers={"X-Api-Key": "change_me_admin"})
    assert r.status_code == 403
    assert _create(client, headers={"X-Api-Key": "change_me_admin"}).status_code == 403
    assert sec.list_users() == []


def test_default_admin_api_key_still_works_outside_production(client, monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("SOVEREIGN_ADMIN_KEY", "change_me_admin")
    assert client.get("/auth/users", headers={"X-Api-Key": "change_me_admin"}).status_code == 200


def test_real_admin_key_and_admin_sessions_work_in_production(client, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    assert client.get("/auth/users", headers=ADMIN).status_code == 200
    sec.create_user("boss@example.org", PW, "admin")
    assert client.get("/auth/users", headers=_bearer(client, "boss@example.org")).status_code == 200


def test_login_racing_a_password_reset_gets_no_session(db, monkeypatch):
    """A reset landing between the password check and the session insert must not leave a live session."""
    uid = sec.create_user("race@example.org", PW)
    real = sec._password_ok

    def check_then_reset(password, h):
        ok = real(password, h)
        sec.set_password(uid, NEW_PW)  # admin reset lands right after verification
        return ok

    monkeypatch.setattr(sec, "_password_ok", check_then_reset)
    assert sec.login_user("race@example.org", PW) is None
    with sqlite3.connect(db) as c:
        assert c.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 0


def test_login_racing_a_deactivation_gets_no_session(db, monkeypatch):
    uid = sec.create_user("race@example.org", PW, "viewer")
    sec.create_user("keep@example.org", PW, "admin")
    real = sec._password_ok

    def check_then_deactivate(password, h):
        ok = real(password, h)
        sec.update_user(uid, is_active=False)
        return ok

    monkeypatch.setattr(sec, "_password_ok", check_then_deactivate)
    assert sec.login_user("race@example.org", PW) is None


def test_no_store_on_every_success_response(client):
    uid = _create(client, "a@example.org").json()["id"]
    h = _bearer(client, "a@example.org")
    responses = [
        client.get("/auth/users", headers=ADMIN),
        client.patch(f"/auth/users/{uid}", json={"role": "editor"}, headers=ADMIN),
        client.put(f"/auth/users/{uid}/password", json={"password": NEW_PW}, headers=ADMIN),
    ]
    h2 = _bearer(client, "a@example.org", NEW_PW)
    responses.append(_change(client, h2, current=NEW_PW, new="third-long-passphrase"))
    assert [r.status_code for r in responses] == [200, 200, 204, 204]
    assert all(r.headers.get("cache-control") == "no-store" for r in responses)


# ── CORS (browser clients on another origin) ─────────────────────────────────

@pytest.mark.parametrize("method", ["GET", "POST", "PATCH", "PUT"])
def test_cors_preflight_allows_account_routes_from_allowed_origin(client, method):
    """TestClient never does CORS; a browser preflights PATCH/PUT with Authorization + JSON."""
    r = client.options(
        "/auth/users/1",
        headers={
            "Origin": "http://localhost:8000",
            "Access-Control-Request-Method": method,
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert r.status_code == 200, r.text
    assert method in r.headers["access-control-allow-methods"]


def test_cors_preflight_refuses_unknown_origin(client):
    r = client.options(
        "/auth/users/1",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "PATCH"},
    )
    assert "access-control-allow-origin" not in r.headers

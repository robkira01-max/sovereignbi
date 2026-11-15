"""P-067 : abonnements courriel aux bulletins."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import pytest
import yaml
from fastapi.testclient import TestClient

os.environ.setdefault("SOVEREIGN_EMBEDDER", "tfidf")
from app.subscriptions import mailer, service, store  # noqa: E402

VIEWER = {"X-Api-Key": "test-viewer-key-s6"}
EDITOR = {"X-Api-Key": "test-editor-key-s6"}
UTC = timezone.utc


def sub(**kw) -> store.Subscription:
    d = dict(id="s1", dashboard_id="d1", email="a@example.org", frequency="weekly", hour_utc=7, weekday=0,
             created_at="2026-01-01T00:00:00+00:00")
    d.update(kw)
    return store.Subscription(**d)


# ── échéances ────────────────────────────────────────────────────────────────

MON_8H = datetime(2026, 11, 16, 8, 0, tzinfo=UTC)      # un lundi


def test_weekly_due_after_slot_and_not_twice():
    s = sub()
    assert store.is_due(s, MON_8H)
    s.last_sent_at = MON_8H.isoformat()
    assert not store.is_due(s, MON_8H + timedelta(days=3))
    assert store.is_due(s, MON_8H + timedelta(days=7))


def test_weekly_not_due_before_the_hour_if_already_served_last_week():
    s = sub(last_sent_at=datetime(2026, 11, 9, 7, 5, tzinfo=UTC).isoformat())
    assert not store.is_due(s, datetime(2026, 11, 16, 6, 59, tzinfo=UTC))
    assert store.is_due(s, datetime(2026, 11, 16, 7, 0, tzinfo=UTC))


def test_new_subscription_does_not_get_a_past_slot():
    s = sub(created_at=MON_8H.isoformat())             # créé lundi 8 h, créneau de 7 h déjà passé
    assert not store.is_due(s, MON_8H + timedelta(hours=1))
    assert store.is_due(s, MON_8H + timedelta(days=7))


def test_daily_and_monthly():
    d = sub(frequency="daily", hour_utc=6, created_at="2026-11-01T00:00:00+00:00")
    assert store.is_due(d, datetime(2026, 11, 16, 6, 30, tzinfo=UTC))
    d.last_sent_at = datetime(2026, 11, 16, 6, 30, tzinfo=UTC).isoformat()
    assert not store.is_due(d, datetime(2026, 11, 16, 23, 0, tzinfo=UTC))
    assert store.is_due(d, datetime(2026, 11, 17, 6, 0, tzinfo=UTC))
    m = sub(frequency="monthly", day_of_month=5, created_at="2026-01-01T00:00:00+00:00",
            last_sent_at=datetime(2026, 11, 5, 7, 0, tzinfo=UTC).isoformat())
    assert not store.is_due(m, datetime(2026, 12, 4, 9, 0, tzinfo=UTC))
    assert store.is_due(m, datetime(2026, 12, 5, 8, 0, tzinfo=UTC))
    # janvier, abonné créé en décembre : l'échéance du 20 décembre est servie
    early = sub(frequency="monthly", day_of_month=20, created_at="2025-12-01T00:00:00+00:00")
    assert store.is_due(early, datetime(2026, 1, 2, 9, 0, tzinfo=UTC))


def test_inactive_never_due():
    assert not store.is_due(sub(active=False), MON_8H)


# ── validation ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("email", ["x", "a@b", "a b@c.org", "a@@c.org", "a@c..org", "a\r\nBcc: x@y.org@c.org", ""])
def test_bad_emails_refused(email):
    with pytest.raises(store.SubscriptionError):
        store.validate("d1", email, "weekly", 7, 0, 1)


@pytest.mark.parametrize("args", [("d1", "a@c.org", "hourly", 7, 0, 1), ("d1", "a@c.org", "weekly", 24, 0, 1),
                                  ("d1", "a@c.org", "weekly", 7, 7, 1), ("d1", "a@c.org", "monthly", 7, 0, 29),
                                  ("../x", "a@c.org", "weekly", 7, 0, 1)])
def test_bad_parameters_refused(args):
    with pytest.raises(store.SubscriptionError):
        store.validate(*args)


def test_domain_allowlist(monkeypatch):
    monkeypatch.setenv("SOVEREIGN_SUBSCRIPTION_DOMAINS", "instad.dj, mef.gouv.dj")
    assert store.validate("d1", "Agent@INSTAD.dj", "weekly", 7, 0, 1) == "agent@instad.dj"
    with pytest.raises(store.SubscriptionError):
        store.validate("d1", "x@gmail.com", "weekly", 7, 0, 1)


# ── mailer ───────────────────────────────────────────────────────────────────

def test_mailer_rejects_header_injection():
    with pytest.raises(mailer.MailError):
        mailer.build("a@b.org\nBcc: x@y.org", "s", "<p>", "t")
    with pytest.raises(mailer.MailError):
        mailer.build("a@b.org", "s\r\nBcc: x", "<p>", "t")


def test_mailer_outbox_when_no_smtp(monkeypatch, tmp_path):
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.setattr(mailer, "OUTBOX", tmp_path)
    assert mailer.send(mailer.build("a@b.org", "Sujet", "<p>x</p>", "x", "https://h/u")) == "outbox"
    files = list(tmp_path.glob("*.eml"))
    assert len(files) == 1 and b"List-Unsubscribe: <https://h/u>" in files[0].read_bytes()


def test_mailer_smtp_failure_hides_details(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "127.0.0.1")
    monkeypatch.setenv("SMTP_PORT", "1")
    monkeypatch.setenv("SMTP_PASSWORD", "secret-pw")
    with pytest.raises(mailer.MailError) as e:
        mailer.send(mailer.build("a@b.org", "s", "<p>", "t"))
    assert "secret-pw" not in str(e.value) and "127.0.0.1" not in str(e.value)


# ── API ──────────────────────────────────────────────────────────────────────

@pytest.fixture()
def env(monkeypatch, tmp_path):
    from app.data.duckdb_store import DataStore
    from app.main import app
    monkeypatch.delenv("SOVEREIGN_DB_PATH", raising=False)
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SOVEREIGN_SUBSCRIPTION_DOMAINS", raising=False)
    monkeypatch.setenv("SOVEREIGN_PUBLIC_URL", "https://bi.example.org")
    monkeypatch.setattr(store, "PATH", tmp_path / "subs.json")
    monkeypatch.setattr(mailer, "OUTBOX", tmp_path / "outbox")
    dd = tmp_path / "dash"; dd.mkdir()
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", dd)
    monkeypatch.setattr(app.state, "store", DataStore(), raising=False)
    tile = {"id": "t1", "type": "table", "title": "Chômage", "sql_pinned": "SELECT 'Obock' AS region, 29.1 AS taux"}
    (dd / "d1.yaml").write_text(yaml.safe_dump({
        "id": "d1", "title": "Tableau <b>1</b>", "scope": "personal", "tiles": [tile],
        "theme": {"primary_color": "#1a4a8c", "font": "sans-serif", "logo_url": ""}, "created_at": "", "updated_at": ""}))
    with TestClient(app) as c:
        yield c, tmp_path, app


def create(c, **kw):
    return c.post("/subscriptions", json={"dashboard_id": "d1", "email": "agent@example.org", **kw}, headers=EDITOR)


def test_requires_roles(env):
    c, *_ = env
    assert c.post("/subscriptions", json={}).status_code == 401
    assert c.post("/subscriptions", json={"dashboard_id": "d1", "email": "a@b.org"}, headers=VIEWER).status_code == 403
    assert c.get("/subscriptions", headers=VIEWER).status_code == 403          # adresses = données personnelles
    assert c.get("/subscriptions/status", headers=VIEWER).status_code == 200


def test_create_list_delete_never_leaks_secret(env):
    c, *_ = env
    r = create(c)
    assert r.status_code == 201 and "unsub_secret" not in r.json()
    assert create(c).status_code == 409                                      # doublon
    assert create(c, email="pas-un-courriel").status_code == 422
    assert c.post("/subscriptions", json={"dashboard_id": "absent", "email": "a@b.org"}, headers=EDITOR).status_code == 422
    body = c.get("/subscriptions", headers=EDITOR).json()
    assert body["count"] == 1 and "unsub_secret" not in str(body)
    assert c.delete(f"/subscriptions/{r.json()['id']}", headers=EDITOR).status_code == 204
    assert c.delete(f"/subscriptions/{r.json()['id']}", headers=EDITOR).status_code == 404


def test_send_now_writes_html_escaped_message_with_unsubscribe(env):
    c, tmp, _ = env
    sid = create(c).json()["id"]
    r = c.post(f"/subscriptions/{sid}/send-now", headers=EDITOR)
    assert r.status_code == 200 and r.json()["channel"] == "outbox"
    import email
    from email import policy
    m = email.message_from_bytes(next((tmp / "outbox").glob("*.eml")).read_bytes(), policy=policy.default)
    assert m["To"] == "agent@example.org"
    assert m["List-Unsubscribe"].startswith("<https://bi.example.org/subscriptions/unsubscribe?id=")
    body = m.get_body(preferencelist=("html",)).get_content()
    assert "&lt;b&gt;1&lt;/b&gt;" in body and "<b>1</b>" not in body       # titre échappé dans le corps HTML
    assert "se désabonner" in body
    assert c.get("/subscriptions", headers=EDITOR).json()["subscriptions"][0]["last_sent_at"]


def test_no_unsubscribe_link_without_https_public_url(env, monkeypatch):
    c, tmp, _ = env
    monkeypatch.setenv("SOVEREIGN_PUBLIC_URL", "http://bi.example.org")
    sid = create(c).json()["id"]
    c.post(f"/subscriptions/{sid}/send-now", headers=EDITOR)
    assert b"List-Unsubscribe" not in next((tmp / "outbox").glob("*.eml")).read_bytes()


def test_unsubscribe_flow_needs_valid_token_and_post(env):
    c, *_ = env
    sid = create(c).json()["id"]
    s = store.get(sid)
    tok = store.unsubscribe_token(s)
    assert c.get("/subscriptions/unsubscribe", params={"id": sid, "token": "faux"}).status_code == 404
    assert c.post("/subscriptions/unsubscribe", data={"id": sid, "token": "faux"}).status_code == 404
    g = c.get("/subscriptions/unsubscribe", params={"id": sid, "token": tok})
    assert g.status_code == 200 and store.get(sid) is not None             # GET ne supprime pas (préchargement)
    assert "agent@example.org" in g.text
    assert c.post("/subscriptions/unsubscribe", data={"id": sid, "token": tok}).status_code == 200
    assert store.get(sid) is None
    assert c.post("/subscriptions/unsubscribe", data={"id": sid, "token": tok}).status_code == 404


def test_run_due_sends_once_and_isolates_failures(env):
    c, tmp, app = env
    ok = create(c).json()["id"]
    c.post("/subscriptions", json={"dashboard_id": "d1", "email": "b@example.org"}, headers=EDITOR)
    store.add(sub(id="gone", dashboard_id="absent", email="c@example.org", created_at="2026-01-01T00:00:00+00:00"))
    from app.routers.dashboards import _DASHBOARDS_DIR
    now = datetime.now(tz=UTC) + timedelta(days=8)
    r1 = service.run_due(app.state.store, _DASHBOARDS_DIR, now)
    assert r1 == {"sent": 2, "failed": 1}
    assert len(list((tmp / "outbox").glob("*.eml"))) == 2
    assert service.run_due(app.state.store, _DASHBOARDS_DIR, now) == {"sent": 0, "failed": 0}   # pas de renvoi
    gone = store.get("gone")
    assert gone.last_error and "introuvable" in gone.last_error
    assert store.get(ok).last_error is None


def test_corrupt_file_fails_loudly_not_silently(env):
    c, tmp, _ = env
    store.PATH.write_text("{pas du json")
    assert create(c).status_code == 422

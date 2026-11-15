"""P-064 : export/suppression de compte et registre d'incidents."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app import feedback
from app.auth import security as sec
from app.compliance import account_data, incidents, models
from app.subscriptions import store as subs

ADMIN = {"X-Api-Key": "test-admin-key-sprint3"}
EDITOR = {"X-Api-Key": "test-editor-key-s6"}
VIEWER = {"X-Api-Key": "test-viewer-key-s6"}
PW = "correct-horse-battery"


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("SOVEREIGN_AUTH_DB", str(tmp_path / "auth.db"))
    monkeypatch.setattr(feedback, "AUDIT_PATH", tmp_path / "audit.jsonl")
    monkeypatch.setattr(models, "CONSENT_PATH", tmp_path / "consents.jsonl")
    monkeypatch.setattr(models, "REQUESTS_PATH", tmp_path / "requests.jsonl")
    monkeypatch.setattr(subs, "PATH", tmp_path / "subs.json")
    monkeypatch.setattr(incidents, "PATH", tmp_path / "incidents.jsonl")
    sec.init_auth_db()
    from app.main import app
    with TestClient(app) as c:
        yield c, tmp_path
    app.state.active_sector_id = None
    app.state.active_semantic_text = None


def seed(tmp):
    admin = sec.create_user("boss@example.org", PW, "admin")
    uid = sec.create_user("agent@example.org", PW, "viewer")
    other = sec.create_user("other@example.org", PW, "viewer")
    models.record_consent("agent@example.org", "cgu", True, path=tmp / "consents.jsonl")
    models.record_consent("other@example.org", "cgu", True, path=tmp / "consents.jsonl")
    models.create_subject_request("agent@example.org", "export", "demande perso", path=tmp / "requests.jsonl")
    models.create_subject_request("other@example.org", "access", "autre", path=tmp / "requests.jsonl")
    subs.add(subs.Subscription(id="s1", dashboard_id="d1", email="agent@example.org", created_at="2026-01-01T00:00:00+00:00"))
    subs.add(subs.Subscription(id="s2", dashboard_id="d1", email="other@example.org", created_at="2026-01-01T00:00:00+00:00"))
    return admin, uid, other, None


def test_routes_are_admin_only(env):
    c, tmp = env
    _, uid, *_ = seed(tmp)
    for m, url in (("get", f"/compliance/account/{uid}/export"), ("delete", f"/compliance/account/{uid}?confirm=x"),
                   ("post", "/compliance/incidents"), ("get", "/compliance/incidents")):
        assert getattr(c, m)(url, headers=EDITOR).status_code == 403
        assert getattr(c, m)(url).status_code == 401


def test_export_contains_only_that_account(env):
    c, tmp = env
    _, uid, *_ = seed(tmp)
    r = c.get(f"/compliance/account/{uid}/export", headers=ADMIN)
    assert r.status_code == 200
    body = r.json()
    assert body["account"]["email"] == "agent@example.org"
    assert len(body["consents"]) == 1 and len(body["access_requests"]) == 1
    assert [s["id"] for s in body["email_subscriptions"]] == ["s1"]
    text = json.dumps(body)
    assert "other@example.org" not in text and "unsub_secret" not in text and "password" not in text
    assert body["not_included"]
    assert c.get("/compliance/account/9999/export", headers=ADMIN).status_code == 404


def test_erase_requires_exact_email_confirmation(env):
    c, tmp = env
    _, uid, *_ = seed(tmp)
    assert c.delete(f"/compliance/account/{uid}", params={"confirm": "autre@example.org"}, headers=ADMIN).status_code == 409
    assert sec.get_user(uid) is not None
    assert c.delete(f"/compliance/account/{uid}", headers=ADMIN).status_code == 422          # confirm obligatoire


def test_erase_removes_account_data_and_keeps_other_users(env):
    c, tmp = env
    _, uid, other, _t = seed(tmp)
    r = c.delete(f"/compliance/account/{uid}", params={"confirm": "AGENT@example.org"}, headers=ADMIN)
    assert r.status_code == 200
    assert r.json()["consents_deleted"] == 1 and r.json()["requests_pseudonymised"] == 1 and r.json()["subscriptions_deleted"] == 1
    assert sec.get_user(uid) is None and sec.get_user(other) is not None
    assert [s.id for s in subs.list_all()] == ["s2"]
    raw = (tmp / "consents.jsonl").read_text() + (tmp / "requests.jsonl").read_text()
    assert "agent@example.org" not in raw and "demande perso" not in raw and "other@example.org" in raw
    assert "erased:" in raw                                            # preuve de traitement conservée, sans identité
    audit = (tmp / "audit.jsonl").read_text()
    assert "account_erased" in audit and "agent@example.org" not in audit
    assert feedback.load_audit  # la chaîne reste lisible
    assert c.delete(f"/compliance/account/{uid}", params={"confirm": "agent@example.org"}, headers=ADMIN).status_code == 404


def test_cannot_erase_last_active_admin(env):
    c, tmp = env
    admin, *_ = seed(tmp)
    r = c.delete(f"/compliance/account/{admin}", params={"confirm": "boss@example.org"}, headers=ADMIN)
    assert r.status_code == 409 and "dernier administrateur" in r.json()["detail"]
    assert sec.get_user(admin) is not None


def test_erase_revokes_sessions(env):
    c, tmp = env
    _, uid, *_ = seed(tmp)
    token = sec.login_user("agent@example.org", PW)
    assert token and sec.verify_session(token)
    account_data.erase_account(uid, "agent@example.org")
    assert sec.verify_session(token) is None


def test_corrupt_compliance_file_aborts_before_touching_anything(env):
    c, tmp = env
    _, uid, *_ = seed(tmp)
    (tmp / "consents.jsonl").write_text("pas du json\n")
    with pytest.raises(account_data.AccountError):
        account_data.export_account(uid)


# ── incidents ────────────────────────────────────────────────────────────────

def mk(c, **kw):
    body = {"detected_at": datetime.now(tz=timezone.utc).isoformat(), "severity": "high", "category": "accès non autorisé",
            "description": "Compte de service utilisé depuis une adresse inattendue.", "personal_data_involved": True}
    body.update(kw)
    return c.post("/compliance/incidents", json=body, headers=ADMIN)


def test_incident_lifecycle_and_audit(env):
    c, tmp = env
    r = mk(c)
    assert r.status_code == 201 and r.json()["status"] == "open"
    iid = r.json()["id"]
    u = c.put(f"/compliance/incidents/{iid}", json={"status": "contained", "action": "Clé API révoquée"}, headers=ADMIN)
    assert u.status_code == 200 and u.json()["status"] == "contained" and "Clé API révoquée" in u.json()["actions"][0]
    u = c.put(f"/compliance/incidents/{iid}", json={"status": "resolved", "clients_notified_at": "2026-11-16T10:00:00+00:00"}, headers=ADMIN)
    assert u.json()["resolved_at"] and u.json()["clients_notified_at"]
    assert c.get("/compliance/incidents", params={"status": "open"}, headers=ADMIN).json()["count"] == 0
    audit = (tmp / "audit.jsonl").read_text()
    assert "incident_opened" in audit and "incident_updated" in audit and "Compte de service" not in audit
    assert oct((tmp / "incidents.jsonl").stat().st_mode & 0o777) == "0o600"


@pytest.mark.parametrize("kw", [{"severity": "énorme"}, {"category": " "}, {"description": ""}, {"detected_at": "hier"}])
def test_incident_validation(env, kw):
    c, _ = env
    assert mk(c, **kw).status_code == 422


def test_incident_update_validation(env):
    c, _ = env
    iid = mk(c).json()["id"]
    assert c.put(f"/compliance/incidents/{iid}", json={"status": "fermé"}, headers=ADMIN).status_code == 422
    assert c.put(f"/compliance/incidents/{iid}", json={"clients_notified_at": "demain"}, headers=ADMIN).status_code == 422
    assert c.put("/compliance/incidents/inconnu", json={"status": "open"}, headers=ADMIN).status_code == 404


def test_overdue_notification_flag(env):
    c, _ = env
    old = (datetime.now(tz=timezone.utc) - timedelta(hours=100)).isoformat()
    late = mk(c, detected_at=old).json()["id"]
    mk(c, personal_data_involved=False, detected_at=old)                      # sans données personnelles : pas concerné
    fine = mk(c, detected_at=old).json()["id"]
    c.put(f"/compliance/incidents/{fine}", json={"clients_notified_at": datetime.now(tz=timezone.utc).isoformat()}, headers=ADMIN)
    mk(c)                                                                      # récent
    assert c.get("/compliance/incidents", headers=ADMIN).json()["overdue_notifications"] == [late]


def test_corrupt_register_is_not_overwritten(env):
    c, tmp = env
    (tmp / "incidents.jsonl").write_text("{cassé\n")
    assert mk(c).status_code == 500                                            # erreur claire, pas de silence
    assert (tmp / "incidents.jsonl").read_text() == "{cassé\n"

"""P-083 : identité par personne — clés API personnelles, clés d'environnement héritées, inventaire des écritures de tables."""
from __future__ import annotations

import re
import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import feedback
from app.auth import apikeys
from app.auth import router as auth_router
from app.auth import security as sec

PW = "Un-mot-de-passe-long-1"
LEGACY_ADMIN = {"X-Api-Key": "test-admin-key-sprint3"}
LEGACY_EDITOR = {"X-Api-Key": "test-editor-key-s6"}
LEGACY_VIEWER = {"X-Api-Key": "test-viewer-key-s6"}
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("SOVEREIGN_AUTH_DB", str(tmp_path / "auth.db"))
    monkeypatch.setattr(feedback, "AUDIT_PATH", tmp_path / "audit.jsonl")
    monkeypatch.setenv("SOVEREIGN_AUDIT_DOCS_DIR", str(tmp_path / "docs"))
    auth_router._throttle.reset()
    sec.init_auth_db()
    from app.main import app
    with TestClient(app) as c:
        yield c, tmp_path
    auth_router._throttle.reset()


def person(c, role="editor", email=None):
    email = email or f"{role}-{len(sec.list_users())}@example.org"
    uid = sec.create_user(email, PW, role)
    r = c.post("/auth/login", json={"email": email, "password": PW})
    assert r.status_code == 200, r.text
    return uid, {"Authorization": f"Bearer {r.json()['token']}"}


def new_key(c, sess, label="ci", ttl=90):
    r = c.post("/auth/keys", json={"label": label, "ttl_days": ttl}, headers=sess)
    assert r.status_code == 201, r.text
    return r.json()


def kh(raw):
    return {"X-Api-Key": raw}


def audit_lines(tmp):
    import json
    return [json.loads(x) for x in (tmp / "audit.jsonl").read_text().splitlines() if x.strip()]


# ── création : une seule fois, format, stockage ─────────────────────────────

def test_key_is_shown_once_has_fixed_prefix_and_only_its_hash_is_stored(env):
    c, tmp = env
    uid, s = person(c)
    k = new_key(c, s)
    raw = k["key"]
    assert raw.startswith("mzb_") and len(raw) >= 40 and k["key_prefix"] == raw[:12]
    assert all("key" not in x for x in c.get("/auth/keys", headers=s).json())        # jamais renvoyée ensuite
    assert raw.encode() not in (tmp / "auth.db").read_bytes()                       # aucune clé en clair dans une copie de la base
    assert raw.encode() not in (tmp / "auth.db-wal").read_bytes() if (tmp / "auth.db-wal").exists() else True
    con = sqlite3.connect(tmp / "auth.db")
    (h,) = con.execute("SELECT key_hash FROM api_keys").fetchone()
    assert len(h) == 64 and raw not in h and "no-store" in c.post("/auth/keys", json={}, headers=s).headers["cache-control"]
    assert raw not in (tmp / "audit.jsonl").read_text()                              # ni dans le journal


def test_only_owner_creates_and_a_key_cannot_mint_keys(env):
    c, _ = env
    uid, s = person(c)
    raw = new_key(c, s)["key"]
    assert c.post("/auth/keys", json={}, headers=kh(raw)).status_code == 403
    assert c.post("/auth/keys", json={}, headers=LEGACY_ADMIN).status_code == 403
    assert c.get("/auth/keys", headers=kh(raw)).status_code == 403
    assert "user_id" not in KeyCreateFields()


def KeyCreateFields():
    from app.auth.keys_router import KeyCreate
    return KeyCreate.model_fields


def test_limits_on_lifetime_and_active_count(env):
    c, _ = env
    _, s = person(c)
    assert c.post("/auth/keys", json={"ttl_days": 366}, headers=s).status_code == 422
    assert c.post("/auth/keys", json={"ttl_days": 0}, headers=s).status_code == 422
    for _i in range(apikeys.MAX_ACTIVE_PER_USER):
        new_key(c, s)
    assert c.post("/auth/keys", json={}, headers=s).status_code == 422


# ── deux personnes, deux acteurs ────────────────────────────────────────────

def test_two_people_two_keys_two_distinct_actors_and_audit_chain_stays_valid(env):
    c, tmp = env
    a, sa = person(c, "editor", "a@example.org")
    b, sb = person(c, "editor", "b@example.org")
    ka, kb = new_key(c, sa), new_key(c, sb)
    by = {}
    for k in (ka, kb):
        r = c.post("/audit-data/documents", files={"file": ("x.csv", f"Date;Compte;Montant\n01/01/2026;{k['id']};1\n".encode())}, headers=kh(k["key"]))
        assert r.status_code == 201, r.text
        by[k["id"]] = r.json()["document"]["uploaded_by"]
    assert by[ka["id"]] == f"user:{a}" and by[kb["id"]] == f"user:{b}" and by[ka["id"]] != by[kb["id"]]
    ev = [e["details"] for e in audit_lines(tmp) if e["details"].get("auth_method") == "api_key"]
    assert {d["key_id"] for d in ev} == {ka["id"], kb["id"]}
    assert all(d["auth_method"] == "api_key" and d["key_ref"] in (ka["key_prefix"], kb["key_prefix"]) for d in ev)
    r = c.get("/audit/verify", headers=LEGACY_ADMIN)
    assert r.status_code == 200 and r.json()["valid"] is True


def test_legacy_actor_is_explicitly_not_attributable_and_carries_a_fingerprint_not_the_key(env):
    c, tmp = env
    r = c.post("/audit-data/documents", files={"file": ("x.csv", b"Date;Compte;Montant\n03/01/2026;41;9\n")}, headers=LEGACY_EDITOR)
    assert r.status_code == 201
    by = r.json()["document"]["uploaded_by"]
    assert re.fullmatch(r"legacy:editor:[0-9a-f]{8}", by) and "test-editor-key" not in by


# ── révocation, rôle, désactivation, expiration : immédiat ──────────────────

def test_revocation_is_immediate_and_attributed(env):
    c, tmp = env
    uid, s = person(c)
    k = new_key(c, s)
    assert c.get("/financial/formulas", headers=kh(k["key"])).status_code != 401
    assert c.delete(f"/auth/keys/{k['id']}", headers=s).status_code == 200
    assert c.get("/financial/formulas", headers=kh(k["key"])).status_code == 401
    ev = [e for e in audit_lines(tmp) if e["action"] == "api_key_revoked"][-1]["details"]
    assert ev["revoked_by"] == uid and ev["by_owner"] is True


def test_role_is_read_from_the_user_on_every_request_not_copied_into_the_key(env):
    c, _ = env
    uid, s = person(c, "editor")
    k = new_key(c, s)
    h = kh(k["key"])
    assert c.get("/financial/formulas", headers=h).status_code == 200
    sec.update_user(uid, role="viewer")
    r = c.post("/financial/runs", json={"formula_code": "BUD001", "inputs": {"depenses": "1", "budget_vote": "2"}}, headers=h)
    assert r.status_code == 403                    # rétrogradation : joue à la requête suivante


def test_deactivating_or_erasing_the_account_kills_its_keys(env):
    c, _ = env
    u1, s1 = person(c, "editor", "d1@example.org")
    u2, s2 = person(c, "editor", "d2@example.org")
    k1, k2 = new_key(c, s1), new_key(c, s2)
    sec.update_user(u1, is_active=False)
    assert c.get("/financial/formulas", headers=kh(k1["key"])).status_code == 401
    sec.update_user(u1, is_active=True)
    assert c.get("/financial/formulas", headers=kh(k1["key"])).status_code == 401      # révoquée, pas seulement ignorée
    from app.compliance import account_data
    account_data.erase_account(u2, "d2@example.org")
    assert c.get("/financial/formulas", headers=kh(k2["key"])).status_code == 401
    assert sqlite3.connect(sec._auth_db_path()).execute("SELECT count(*) FROM api_keys WHERE user_id=?", (u2,)).fetchone()[0] == 0


def test_expired_key_is_refused(env, monkeypatch):
    c, _ = env
    _, s = person(c)
    k = new_key(c, s, ttl=1)
    con = sqlite3.connect(sec._auth_db_path())
    con.execute("UPDATE api_keys SET expires_at=? WHERE id=?", ((apikeys._now() - timedelta(seconds=1)).isoformat(), k["id"]))
    con.commit()
    r = c.get("/financial/formulas", headers=kh(k["key"]))
    assert r.status_code == 401 and "expirée" in r.json()["detail"]


def test_unknown_and_malformed_keys_get_the_same_refusal(env):
    c, _ = env
    for bad in ("mzb_" + "x" * 43, "mzb_", "mzb_" + "y" * 500, "nimporte"):
        r = c.get("/financial/formulas", headers=kh(bad))
        assert r.status_code == 401


def test_rotation_replaces_the_key_and_only_the_owner_can_rotate(env):
    c, _ = env
    _, s = person(c, "editor", "r1@example.org")
    _, other = person(c, "editor", "r2@example.org")
    k = new_key(c, s)
    assert c.post(f"/auth/keys/{k['id']}/rotate", headers=other).status_code == 404
    n = c.post(f"/auth/keys/{k['id']}/rotate", headers=s).json()
    assert n["key"] != k["key"] and n["id"] != k["id"]
    assert c.get("/financial/formulas", headers=kh(k["key"])).status_code == 401
    assert c.get("/financial/formulas", headers=kh(n["key"])).status_code == 200


def test_admin_can_revoke_others_but_a_plain_user_cannot_and_gets_404(env):
    c, _ = env
    _, admin = person(c, "admin", "adm@example.org")
    _, u1 = person(c, "editor", "u1@example.org")
    _, u2 = person(c, "editor", "u2@example.org")
    k = new_key(c, u1)
    assert c.delete(f"/auth/keys/{k['id']}", headers=u2).status_code == 404
    assert c.get("/auth/keys/all", headers=u2).status_code == 403
    assert c.delete(f"/auth/keys/{k['id']}", headers=admin).status_code == 200
    assert c.get("/financial/formulas", headers=kh(k["key"])).status_code == 401
    assert c.get("/auth/keys/all", headers=admin).status_code == 200


def test_key_is_not_accepted_in_the_url(env):
    c, _ = env
    _, s = person(c)
    raw = new_key(c, s)["key"]
    assert c.get(f"/financial/formulas?api_key={raw}").status_code == 401
    assert c.get(f"/financial/formulas?x_api_key={raw}").status_code == 401


def test_last_use_is_written_at_most_once_a_minute(env):
    c, _ = env
    _, s = person(c)
    k = new_key(c, s)
    con = sqlite3.connect(sec._auth_db_path())
    get = lambda: con.execute("SELECT last_used_at FROM api_keys WHERE id=?", (k["id"],)).fetchone()[0]    # noqa: E731
    assert get() is None
    c.get("/financial/formulas", headers=kh(k["key"]))
    first = get()
    assert first
    c.get("/financial/formulas", headers=kh(k["key"]))
    assert get() == first


# ── ce qu'une clé n'ouvre pas : résolution, revue, validation, comptes ──────

def test_resolution_requires_a_session_not_any_key(env):
    c, _ = env
    uid, s = person(c, "admin", "res@example.org")
    raw = new_key(c, s)["key"]
    for h in (kh(raw), LEGACY_ADMIN, LEGACY_EDITOR):
        r = c.post("/audit-data/issues/00000000-0000-0000-0000-000000000000/resolve", json={"justification": "Une justification"}, headers=h)
        assert r.status_code == 403 and "sessions nominatives" in r.json()["detail"]
    assert c.get("/auth/users", headers=kh(raw)).status_code == 403            # gestion des comptes : session seulement


def test_a_personal_key_allows_read_import_and_run(env):
    c, _ = env
    _, s = person(c, "editor")
    h = kh(new_key(c, s)["key"])
    assert c.get("/financial/formulas", headers=h).status_code == 200
    assert c.post("/audit-data/documents", files={"file": ("x.csv", b"Date;Compte;Montant\n02/01/2026;7;3\n")}, headers=h).status_code in (200, 201)
    r = c.post("/financial/runs", json={"formula_code": "BUD001", "inputs": {"depenses": "57", "budget_vote": "50"}}, headers=h)
    assert r.status_code == 201, r.text


# ── clés héritées : plafond, échéance, démarrage ────────────────────────────

def test_legacy_key_is_read_only_in_production_with_an_explicit_message(env, monkeypatch):
    c, _ = env
    monkeypatch.setenv("APP_ENV", "production")
    r = c.post("/financial/runs", json={"formula_code": "BUD001", "inputs": {"depenses": "1", "budget_vote": "2"}}, headers=LEGACY_EDITOR)
    assert r.status_code == 403 and "lecture seule" in r.json()["detail"] and "mzb_" in r.json()["detail"]
    assert c.get("/financial/formulas", headers=LEGACY_EDITOR).status_code == 200


def test_legacy_key_stops_working_after_the_deadline(env, monkeypatch):
    c, _ = env
    monkeypatch.setenv("SOVEREIGN_LEGACY_KEYS_DEADLINE", (date.today() - timedelta(days=1)).isoformat())
    r = c.get("/financial/formulas", headers=LEGACY_VIEWER)
    assert r.status_code == 401 and "expirée" in r.json()["detail"]
    monkeypatch.setenv("SOVEREIGN_LEGACY_KEYS_DEADLINE", (date.today() + timedelta(days=5)).isoformat())
    assert c.get("/financial/formulas", headers=LEGACY_VIEWER).status_code == 200
    _, s = person(c)
    assert c.get("/financial/formulas", headers=kh(new_key(c, s)["key"])).status_code == 200      # les clés personnelles ne dépendent pas de l'échéance


def test_production_startup_refuses_test_keys_default_keys_and_missing_or_far_deadline(monkeypatch):
    from app.security import legacy_keys as lk
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SOVEREIGN_ADMIN_KEY", "x" * 40)
    monkeypatch.setenv("SOVEREIGN_EDITOR_KEY", "y" * 40)
    monkeypatch.setenv("SOVEREIGN_VIEWER_KEY", "z" * 40)
    with pytest.raises(lk.LegacyConfigError, match="ÉCHÉANCE|échéance"):
        lk.enforce_production_config()
    monkeypatch.setenv("SOVEREIGN_LEGACY_KEYS_DEADLINE", (date.today() + timedelta(days=400)).isoformat())
    with pytest.raises(lk.LegacyConfigError, match="lointaine"):
        lk.enforce_production_config()
    monkeypatch.setenv("SOVEREIGN_LEGACY_KEYS_DEADLINE", (date.today() + timedelta(days=30)).isoformat())
    with pytest.raises(lk.LegacyConfigError, match="VAULT_KEY"):
        lk.enforce_production_config()                                       # secret du coffre obligatoire
    monkeypatch.setenv("SOVEREIGN_VAULT_KEY", "secret-serveur-" + "a" * 30)
    lk.enforce_production_config()                                           # configuration valide : démarre
    for bad in ("test-viewer-key-s6", "test-editor-key-s6", "test-admin-key-sprint3", "change_me_admin"):
        monkeypatch.setenv("SOVEREIGN_VIEWER_KEY", bad)
        with pytest.raises(lk.LegacyConfigError, match="test ou par défaut"):
            lk.enforce_production_config()


def test_startup_warns_while_legacy_keys_exist_and_admin_sees_the_status(env, monkeypatch):
    from app.security import legacy_keys as lk
    c, _ = env
    monkeypatch.setenv("SOVEREIGN_LEGACY_KEYS_DEADLINE", (date.today() + timedelta(days=10)).isoformat())
    assert lk.startup_warnings() and "héritées" in lk.startup_warnings()[0]
    _, admin = person(c, "admin", "st@example.org")
    st = c.get("/auth/keys/legacy-status", headers=admin).json()
    assert st["present"] and st["days_left"] == 10 and st["expired"] is False
    _, u = person(c, "editor", "st2@example.org")
    assert c.get("/auth/keys/legacy-status", headers=u).status_code == 403


# ── sécurité par ligne : la clé hérite des périmètres de son propriétaire ───

def test_personal_key_inherits_the_owner_row_scope(env):
    from app.security import row_policy
    from app.security.principal_mw import _resolve
    c, _ = env
    uid, s = person(c, "editor", "rl@example.org")
    raw = new_key(c, s)["key"]
    p = _resolve({b"x-api-key": raw.encode()})
    assert p == row_policy.Principal("user", uid)
    aid, sa = person(c, "admin", "rla@example.org")
    assert _resolve({b"x-api-key": new_key(c, sa)["key"].encode()}) == row_policy.Principal("admin")
    assert _resolve({b"x-api-key": b"mzb_" + b"q" * 43}) is None


# ── inventaire : tout chemin qui écrit une table passe par la garde ─────────

WRITE = re.compile(r"(CREATE|DROP|ALTER)\s+(OR REPLACE\s+)?(TABLE|VIEW)|INSERT\s+(OR REPLACE\s+)?INTO|DELETE\s+FROM|\bUPDATE\s+\"?\w+\"?\s+SET", re.I)

# module → raison pour laquelle il n'écrit PAS dans l'espace de tables des utilisateurs (DataStore)
ALLOWED_WRITERS = {
    "app/data/duckdb_store.py": "le point d'écriture gardé (load_dataframe / load_trusted_table)",
    "app/audit_data/repo.py": "tables audit_* internes, créées par le produit (réservées ou de confiance)",
    "app/audit_rules/store.py": "historique des contrôles (tables réservées)",
    "app/financial/runs.py": "historique des calculs (tables réservées)",
    "app/security/row_policy.py": "table de règles de sécurité par ligne (connexion propre)",
    "app/cache/persistent_cache.py": "cache SQLite séparé",
    "app/rag/doc_store.py": "magasin documentaire séparé",
    "app/compliance/account_data.py": "base d'authentification (SQLite), pas le DataStore",
    "app/workspace/service.py": "tables workspace_* (réservées, connexion directe) ; chemins disque uniquement via paths.py",
    "app/geo_catalog/importer.py": "connexion DuckDB privée en mémoire, jamais le DataStore partagé",
    "app/geo_catalog/spatial_engine.py": "connexion DuckDB privée en mémoire, jamais le DataStore partagé",
}


def test_every_module_that_writes_tables_is_inventoried():
    offenders = []
    for f in (ROOT / "app").rglob("*.py"):
        rel = str(f.relative_to(ROOT))
        if rel.startswith("app/auth/") or "__pycache__" in rel:
            continue
        if WRITE.search(f.read_text(encoding="utf-8")) and rel not in ALLOWED_WRITERS:
            offenders.append(rel)
    assert not offenders, f"Écriture de table hors inventaire (P-083) : {offenders} — passer par DataStore.load_dataframe ou justifier ici."


def test_scheduled_sync_has_no_direct_table_write_and_uses_the_guarded_loader():
    src = (ROOT / "app/sync/sync_engine.py").read_text(encoding="utf-8")
    assert not WRITE.search(src) and "load_dataframe(" in src


def test_every_caller_of_load_dataframe_is_a_known_user_data_path():
    callers = {str(f.relative_to(ROOT)) for f in (ROOT / "app").rglob("*.py") if ".load_dataframe(" in f.read_text(encoding="utf-8")}
    assert callers <= {"app/routers/addin.py", "app/routers/sdmx.py", "app/routers/connectors.py", "app/rag/doc_pipeline.py",
                       "app/onboarding/sandbox.py", "app/sync/sync_engine.py", "app/data/duckdb_store.py"}, callers


# ── revue sécurité P-083 : non-régression ───────────────────────────────────

def test_admin_session_reaches_the_semantic_routes_but_a_legacy_key_cannot_mutate(env, monkeypatch):
    c, _ = env
    _, admin = person(c, "admin", "adm2@example.org")
    assert c.get("/admin/semantic", headers=admin).status_code == 200
    assert c.post("/admin/versions/snapshot", json={"label": "t"}, headers={"X-Admin-Key": "test-admin-key-sprint3"}).status_code == 403
    monkeypatch.setenv("APP_ENV", "production")
    assert c.get("/admin/semantic", headers={"X-Admin-Key": "test-admin-key-sprint3"}).status_code == 200
    assert c.put("/admin/semantic", json={"schema_version": "2", "tables": []}, headers={"X-Admin-Key": "test-admin-key-sprint3"}).status_code == 403


def test_unknown_app_env_values_are_treated_as_production(monkeypatch):
    from app.security import legacy_keys as lk
    for v in ("prod", "Production ", "staging"):
        monkeypatch.setenv("APP_ENV", v)
        assert lk.is_production()
    for v in ("development", "test", ""):
        monkeypatch.setenv("APP_ENV", v)
        assert not lk.is_production()
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SOVEREIGN_LEGACY_KEYS_READ_ONLY", "0")
    with pytest.raises(lk.LegacyConfigError, match="READ_ONLY"):
        lk.enforce_production_config()


def test_password_change_revokes_personal_keys(env):
    c, _ = env
    uid, s = person(c, "editor", "pw@example.org")
    k = new_key(c, s)
    sec.set_password(uid, "Un-autre-mot-de-passe-2")
    assert c.get("/financial/formulas", headers=kh(k["key"])).status_code == 401


def test_caller_cannot_overwrite_identity_fields_in_the_audit_details(tmp_path):
    from app.security.identity import Identity, current_identity
    tok = current_identity.set(Identity("api_key", "editor", user_id=1, key_id=7, key_ref="mzb_abcd1234"))
    try:
        feedback.record_audit("x", {"key_id": 999, "auth_method": "session"}, path=tmp_path / "a.jsonl")
    finally:
        current_identity.reset(tok)
    import json
    d = json.loads((tmp_path / "a.jsonl").read_text())["details"]
    assert d["key_id"] == 7 and d["auth_method"] == "api_key"


def test_duplicate_api_key_headers_resolve_to_the_first_one_in_the_middleware():
    from app.security.principal_mw import _first_headers
    assert _first_headers([(b"x-api-key", b"A"), (b"x-api-key", b"B")])[b"x-api-key"] == b"A"


def test_legacy_fingerprint_is_keyed_and_production_requires_long_keys(monkeypatch):
    import hashlib

    from app.security import legacy_keys as lk
    monkeypatch.setenv("SOVEREIGN_VAULT_KEY", "secret-serveur-" + "a" * 30)
    a = lk.fingerprint("test-editor-key-s6")
    assert a != hashlib.sha256(b"test-editor-key-s6").hexdigest()[:8]          # plus un SHA-256 nu
    monkeypatch.setenv("SOVEREIGN_VAULT_KEY", "autre-secret-" + "b" * 30)
    assert lk.fingerprint("test-editor-key-s6") != a
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SOVEREIGN_ADMIN_KEY", "courte-mais-pas-par-defaut")
    monkeypatch.setenv("SOVEREIGN_EDITOR_KEY", "")
    monkeypatch.setenv("SOVEREIGN_VIEWER_KEY", "")
    monkeypatch.setenv("SOVEREIGN_LEGACY_KEYS_DEADLINE", (date.today() + timedelta(days=30)).isoformat())
    with pytest.raises(lk.LegacyConfigError, match="trop courte"):
        lk.enforce_production_config()


def test_rotation_is_atomic_and_refuses_inactive_keys(env):
    c, _ = env
    _, s = person(c, "editor", "rot@example.org")
    k = new_key(c, s)
    n = c.post(f"/auth/keys/{k['id']}/rotate", headers=s)
    assert n.status_code == 201
    again = c.post(f"/auth/keys/{k['id']}/rotate", headers=s)                      # ancienne déjà révoquée
    assert again.status_code == 409
    assert len([x for x in c.get("/auth/keys", headers=s).json() if x["status"] == "active"]) == 1

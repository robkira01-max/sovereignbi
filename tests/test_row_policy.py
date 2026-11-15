"""P-068 : sécurité par ligne (échec fermé)."""
from __future__ import annotations

import pandas as pd
import pytest
import yaml
from fastapi.testclient import TestClient

from app import feedback
from app.auth import security as sec
from app.data.duckdb_store import DataStore
from app.security import row_policy as rp

ADMIN = {"X-Api-Key": "test-admin-key-sprint3"}
EDITOR = {"X-Api-Key": "test-editor-key-s6"}
VIEWER = {"X-Api-Key": "test-viewer-key-s6"}
PW = "correct-horse-battery"
POLICY = {"policies": [{"table": "ventes", "column": "region", "scope": "region"}]}


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("SOVEREIGN_AUTH_DB", str(tmp_path / "auth.db"))
    monkeypatch.setenv("SOVEREIGN_ROW_POLICIES", str(tmp_path / "pol.yaml"))
    monkeypatch.setattr(feedback, "AUDIT_PATH", tmp_path / "audit.jsonl")
    (tmp_path / "pol.yaml").write_text(yaml.safe_dump(POLICY))
    sec.init_auth_db()
    store = DataStore()
    store.load_dataframe("ventes", pd.DataFrame({"region": ["Obock", "Obock", "Tadjourah", "Dikhil"], "montant": [1, 2, 10, 100]}))
    store.load_dataframe("regions", pd.DataFrame({"region": ["Obock", "Tadjourah", "Dikhil"], "pop": [5, 6, 7]}))
    u1 = sec.create_user("obock@example.org", PW, "viewer")
    u2 = sec.create_user("nobody@example.org", PW, "editor")
    adm = sec.create_user("adm@example.org", PW, "admin")
    rp.set_scope(u1, "region", ["Obock"])
    return tmp_path, store, u1, u2, adm


def run(store, sql, who):
    with rp.as_principal(who):
        return store.execute(sql)[1]


U = lambda uid: rp.Principal("user", uid)  # noqa: E731


# ── réécriture et filtrage réel ─────────────────────────────────────────────

def test_scoped_user_sees_only_their_rows(env):
    _, store, u1, *_ = env
    assert run(store, "SELECT SUM(montant) FROM ventes", U(u1)) == [(3,)]
    assert run(store, "SELECT region FROM ventes ORDER BY montant", U(u1)) == [("Obock",), ("Obock",)]


def test_admin_sees_everything_and_unprotected_tables_are_untouched(env):
    _, store, u1, *_ = env
    assert run(store, "SELECT SUM(montant) FROM ventes", rp.Principal("admin")) == [(113,)]
    assert len(run(store, "SELECT * FROM regions", U(u1))) == 3            # table non protégée : tout
    assert len(run(store, "SELECT * FROM regions", None)) == 3


@pytest.mark.parametrize("sql", [
    "SELECT SUM(montant) FROM ventes v JOIN regions r ON r.region = v.region",
    "SELECT SUM(montant) FROM ventes AS v, regions r WHERE r.region = v.region",
    "SELECT (SELECT SUM(montant) FROM ventes)",
    "SELECT SUM(montant) FROM (SELECT * FROM ventes) t",
    "WITH x AS (SELECT * FROM ventes) SELECT SUM(montant) FROM x",
    "SELECT SUM(montant) FROM ventes WHERE region IN (SELECT region FROM ventes)",
    "SELECT montant FROM ventes UNION ALL SELECT montant FROM ventes",
    "SELECT SUM(montant) FROM main.ventes",
    "SELECT SUM(VENTES.montant) FROM VENTES",
    "SELECT SUM(montant) FROM ventes WHERE 1=1 OR region = 'Dikhil'",
])
def test_every_reference_is_filtered(env, sql):
    _, store, u1, *_ = env
    rows = run(store, sql, U(u1))
    total = sum(r[0] for r in rows if r[0] is not None)
    assert total in (3, 6), (sql, rows)           # 3 = une lecture ; 6 = UNION ALL de deux lectures filtrées. Jamais 113/10/100.


def test_cte_named_like_protected_table_is_refused(env):
    _, store, u1, *_ = env
    with pytest.raises(rp.AccessDenied):
        run(store, "WITH ventes AS (SELECT * FROM ventes) SELECT SUM(montant) FROM ventes", U(u1))


def test_scope_values_cannot_inject_sql(env):
    _, store, u1, *_ = env
    rp.set_scope(u1, "region", ["x') OR 1=1 --", "Obock"])
    assert run(store, "SELECT SUM(montant) FROM ventes", U(u1)) == [(3,)]


def test_numeric_column_is_compared_as_text(env):
    tmp, store, u1, *_ = env
    store.load_dataframe("ventes", pd.DataFrame({"region": [1, 2, 2], "montant": [5, 6, 7]}))
    rp.set_scope(u1, "region", ["2"])
    assert run(store, "SELECT SUM(montant) FROM ventes", U(u1)) == [(13,)]


# ── échec fermé ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("who", [None, rp.Principal("key")])
def test_no_identity_or_api_key_is_denied_on_protected_tables(env, who):
    _, store, *_ = env
    with pytest.raises(rp.AccessDenied):
        run(store, "SELECT * FROM ventes", who)


def test_user_without_scope_is_denied_not_unrestricted(env):
    _, store, _u1, u2, _ = env
    with pytest.raises(rp.AccessDenied):
        run(store, "SELECT * FROM ventes", U(u2))
    rp.set_scope(_u1, "region", [])                      # retirer le périmètre = refus
    with pytest.raises(rp.AccessDenied):
        run(store, "SELECT * FROM ventes", U(_u1))


def test_unparseable_sql_is_refused_when_policies_active(env):
    _, store, u1, *_ = env
    with pytest.raises(rp.AccessDenied):
        run(store, "SELEC FROM ventes ((", U(u1))


def test_non_select_on_protected_table_is_refused(env):
    _, store, u1, *_ = env
    with pytest.raises(rp.AccessDenied):
        run(store, "DELETE FROM ventes", U(u1))


def test_invalid_policy_file_fails_loudly_and_counts_as_active(env):
    tmp, store, u1, *_ = env
    (tmp / "pol.yaml").write_text("policies: [{table: ventes}]")
    assert rp.active() is True
    with pytest.raises(rp.RowPolicyError):
        run(store, "SELECT 1", rp.Principal("admin"))
    for bad in ("policies: {a: 1}", "policies: [{table: 'v;drop', column: c, scope: s}]", ": : :"):
        (tmp / "pol.yaml").write_text(bad)
        with pytest.raises(rp.RowPolicyError):
            rp.load_policies()


def test_without_policy_file_nothing_changes(env, monkeypatch):
    tmp, store, *_ = env
    monkeypatch.delenv("SOVEREIGN_ROW_POLICIES")                      # aucun chemin demandé et aucun fichier par défaut
    monkeypatch.chdir(tmp)
    assert rp.active() is False
    assert len(run(store, "SELECT * FROM ventes", None)) == 4


def test_ai_prompt_samples_do_not_leak_protected_rows(env):
    _, store, u1, *_ = env

    def ventes_part(text):                      # la table « regions » n'est pas protégée : ses exemples restent visibles
        return text.split("Table ventes")[1]

    with rp.as_principal(U(u1)):
        mine = ventes_part(store.schema_description())
    assert "Obock" in mine and "Dikhil" not in mine and "Tadjourah" not in mine
    with rp.as_principal(None):
        masked = ventes_part(store.schema_description())
    assert "Obock" not in masked and "masqués" in masked


# ── bout en bout (middleware + routes) ──────────────────────────────────────

@pytest.fixture()
def client(env, monkeypatch):
    tmp, store, u1, u2, adm = env
    from app.main import app
    monkeypatch.setattr(app.state, "store", store, raising=False)
    dd = tmp / "dash"; dd.mkdir()
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", dd)
    tile = {"id": "t1", "type": "table", "title": "Ventes", "sql_pinned": "SELECT region, montant FROM ventes ORDER BY montant"}
    (dd / "d1.yaml").write_text(yaml.safe_dump({"id": "d1", "title": "T", "scope": "personal", "tiles": [tile],
        "theme": {"primary_color": "#1a4a8c", "font": "sans-serif", "logo_url": ""}, "created_at": "", "updated_at": ""}))
    with TestClient(app) as c:
        yield c, tmp, u1, u2, adm
    app.state.active_sector_id = None
    app.state.active_semantic_text = None


def bearer(email):
    return {"Authorization": f"Bearer {sec.login_user(email, PW)}"}


def export(c, headers, route="export/csv"):
    return c.get(f"/dashboards/d1/tiles/t1/{route}", headers=headers)


def test_end_to_end_csv_export_per_caller(client):
    c, *_ = client
    mine = export(c, bearer("obock@example.org"))
    assert mine.status_code == 200 and "Obock" in mine.text and "Dikhil" not in mine.text and "Tadjourah" not in mine.text
    assert "Dikhil" in export(c, ADMIN).text
    assert "Dikhil" in export(c, bearer("adm@example.org")).text
    for h in (VIEWER, EDITOR, bearer("nobody@example.org")):
        r = export(c, h)
        assert r.status_code == 422 and "Dikhil" not in r.text and "Obock" not in r.text


def test_end_to_end_sdmx_export_is_filtered_too(client):
    c, *_ = client
    r = export(c, bearer("obock@example.org"), "export/sdmx-csv?value_col=montant")
    assert r.status_code == 200 and "Dikhil" not in r.text and "Obock" in r.text


def test_shared_caches_are_off_when_policies_are_active(client):
    from app.dashboards import insight
    c, *_ = client
    insight.set_cached("t1", "sql", "texte dérivé des lignes")
    assert insight.get_cached("t1", "sql") is None


def test_invalid_session_gets_no_data_not_a_leak(client):
    c, *_ = client
    r = export(c, {"Authorization": "Bearer " + "0" * 64})
    assert r.status_code == 401 and "Dikhil" not in r.text


def test_email_bulletin_never_uses_the_triggering_admins_rights(client):
    from app.subscriptions import mailer, service, store as subs
    c, tmp, *_ = client
    subs.PATH = tmp / "subs.json"
    mailer.OUTBOX = tmp / "outbox"
    from app.main import app
    sub = subs.Subscription(id="s1", dashboard_id="d1", email="x@example.org", created_at="2026-01-01T00:00:00+00:00")
    subs.add(sub, tmp / "subs.json")
    import app.routers.dashboards as D
    with rp.as_principal(rp.Principal("admin")):                    # déclenché par un admin
        service.send_one(sub, app.state.store, D._DASHBOARDS_DIR)
    mail = next((tmp / "outbox").glob("*.eml")).read_text()
    assert "Dikhil" not in mail and "Tadjourah" not in mail         # l'erreur d'accès est rendue, pas les lignes
    assert "refus" in mail.lower() or "protégée" in mail


# ── administration ──────────────────────────────────────────────────────────

def test_admin_routes_require_admin(client):
    c, _, u1, *_ = client
    for m, url in (("get", "/security/row-policies"), ("get", f"/security/users/{u1}/scopes")):
        assert getattr(c, m)(url, headers=EDITOR).status_code == 403
        assert getattr(c, m)(url).status_code == 401
    assert c.put(f"/security/users/{u1}/scopes/region", json={"values": ["x"]}, headers=EDITOR).status_code == 403


def test_scope_management_validates_and_audits(client):
    c, tmp, u1, *_ = client
    assert c.put(f"/security/users/{u1}/scopes/region", json={"values": ["Obock", "Dikhil"]}, headers=ADMIN).json()["values"] == 2
    assert c.get(f"/security/users/{u1}/scopes", headers=ADMIN).json()["scopes"] == {"region": ["Dikhil", "Obock"]}
    assert c.put(f"/security/users/{u1}/scopes/inconnu", json={"values": ["x"]}, headers=ADMIN).status_code == 422
    assert c.put("/security/users/9999/scopes/region", json={"values": ["x"]}, headers=ADMIN).status_code == 404
    assert c.put(f"/security/users/{u1}/scopes/region", json={"values": ["v" * 300]}, headers=ADMIN).status_code == 422
    audit = (tmp / "audit.jsonl").read_text()
    assert "scope_updated" in audit and "Obock" not in audit            # compte seulement, pas les valeurs


def test_policy_diagnostics(client, env):
    c, tmp, *_ = client
    body = c.get("/security/row-policies", headers=ADMIN).json()
    assert body["active"] and body["valid"] and body["policies"][0]["problem"] is None
    (tmp / "pol.yaml").write_text(yaml.safe_dump({"policies": [{"table": "absente", "column": "x", "scope": "s"},
                                                               {"table": "ventes", "column": "nope", "scope": "s"}]}))
    probs = [p["problem"] for p in c.get("/security/row-policies", headers=ADMIN).json()["policies"]]
    assert probs == ["table absente de la base chargée", "colonne introuvable"]
    (tmp / "pol.yaml").write_text("policies: [{table: x}]")
    assert c.get("/security/row-policies", headers=ADMIN).json()["valid"] is False


def test_erasing_an_account_removes_its_scopes(client, monkeypatch):
    from app.compliance import account_data, models
    c, tmp, u1, *_ = client
    monkeypatch.setattr(models, "CONSENT_PATH", tmp / "c.jsonl")
    monkeypatch.setattr(models, "REQUESTS_PATH", tmp / "r.jsonl")
    account_data.erase_account(u1, "obock@example.org")
    with __import__("contextlib").closing(rp._conn()) as db:
        assert db.execute("SELECT COUNT(*) FROM user_scopes WHERE user_id=?", (u1,)).fetchone()[0] == 0


# ── correctifs de la relecture de sécurité ──────────────────────────────────

@pytest.mark.parametrize("content", ["policy:\n - {table: ventes, column: region, scope: region}\n", "Policies: []\n",
                                     "- {table: ventes, column: region, scope: region}\n", "", "{}\n", "policies: []\nextra: 1\n"])
def test_policy_file_typos_never_mean_no_protection(env, content):
    tmp, store, u1, *_ = env
    (tmp / "pol.yaml").write_text(content)
    assert rp.active() is True                      # fichier présent mais invalide = actif, donc échec fermé
    with pytest.raises(rp.RowPolicyError):
        run(store, "SELECT 1", rp.Principal("admin"))


def test_explicit_env_path_that_is_missing_fails_closed(env):
    tmp, store, *_ = env
    (tmp / "pol.yaml").unlink()
    assert rp.active() is True
    with pytest.raises(rp.RowPolicyError):
        rp.load_policies()


def test_policy_changes_are_picked_up_even_with_same_mtime(env):
    import os
    tmp, store, u1, *_ = env
    f = tmp / "pol.yaml"
    assert rp.load_policies()[0].column == "region"
    st = f.stat()
    f.write_text(yaml.safe_dump({"policies": [{"table": "ventes", "column": "region", "scope": "region"},
                                              {"table": "regions", "column": "region", "scope": "region"}]}))
    os.utime(f, ns=(st.st_atime_ns, st.st_mtime_ns))                   # même mtime, taille différente
    assert len(rp.load_policies()) == 2


def test_table_functions_are_refused_when_policies_are_active(env):
    _, store, u1, *_ = env
    with pytest.raises(rp.AccessDenied):
        run(store, "SELECT * FROM range(3)", U(u1))


def test_non_admin_cannot_replace_a_protected_table(env):
    _, store, u1, *_ = env
    df = pd.DataFrame({"region": ["Obock"], "montant": [999]})
    with rp.as_principal(U(u1)), pytest.raises(rp.AccessDenied):
        store.load_dataframe("ventes", df)
    with rp.as_principal(rp.Principal("key")), pytest.raises(rp.AccessDenied):
        store.load_dataframe("Ventes", df)
    store.load_dataframe("autre", df)                                   # table non protégée : permis
    with rp.as_principal(rp.Principal("admin")):
        store.load_dataframe("ventes", df)                              # admin : permis
    store.load_dataframe("ventes", df)                                  # sans identité (démarrage, CLI) : permis


def test_pdf_cached_route_is_off_when_policies_are_active(client):
    c, *_ = client
    r = c.post("/export/pdf-cached", json={"question": "q"}, headers=VIEWER)
    assert r.status_code == 503 and "Cache non disponible" in r.text


def test_mcp_list_tables_does_not_leak_protected_counts(env):
    from app.routers.mcp import _tool_list_tables
    import json
    _, store, u1, *_ = env
    with rp.as_principal(U(u1)):
        mine = json.loads(_tool_list_tables(store)["content"][0]["text"])
    counts = {t["name"]: t["row_count"] for t in mine}
    assert counts["ventes"] == 2 and counts["regions"] == 3             # 2 lignes Obock sur 4
    with rp.as_principal(rp.Principal("key")):
        other = json.loads(_tool_list_tables(store)["content"][0]["text"])
    assert {t["name"]: t["row_count"] for t in other}["ventes"] is None


def test_access_denied_maps_to_403(client):
    c, *_ = client
    r = c.post("/upload", files={"file": ("ventes.csv", b"region,montant\nObock,1\n", "text/csv")}, headers=EDITOR)
    assert r.status_code == 403 and "protégée" in r.json()["detail"]

"""P-069 : jeux de données certifiés."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app import feedback
from app.certification import registry
from app.data.duckdb_store import DataStore

ADMIN = {"X-Api-Key": "test-admin-key-sprint3"}
EDITOR = {"X-Api-Key": "test-editor-key-s6"}
VIEWER = {"X-Api-Key": "test-viewer-key-s6"}


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(registry, "PATH", tmp_path / "certs.json")
    monkeypatch.setattr(feedback, "AUDIT_PATH", tmp_path / "audit.jsonl")
    from app.main import app
    store = DataStore()
    store.load_dataframe("pib", pd.DataFrame({"annee": [2022, 2023], "valeur": [3.1, 3.4]}))
    store.load_dataframe("brouillon", pd.DataFrame({"x": [1]}))
    monkeypatch.setattr(app.state, "store", store, raising=False)
    with TestClient(app) as c:
        yield c, store, tmp_path
    app.state.active_sector_id = None
    app.state.active_semantic_text = None


def certify(c, **kw):
    body = {"table": "pib", "certifier": "INSTAD", "reference": "Note 2026-14 du 12/11/2026"}
    body.update(kw)
    return c.post("/certification", json=body, headers=ADMIN)


def status(c, table="pib"):
    return c.get(f"/certification/{table}", headers=VIEWER).json()


# ── empreinte ────────────────────────────────────────────────────────────────

def test_fingerprint_ignores_row_order_but_not_content_or_schema(env):
    _, store, _ = env
    a = registry.fingerprint(store, "pib")
    store.load_dataframe("pib", pd.DataFrame({"annee": [2023, 2022], "valeur": [3.4, 3.1]}))
    assert registry.fingerprint(store, "pib") == a                                   # ordre : même empreinte
    store.load_dataframe("pib", pd.DataFrame({"annee": [2022, 2023], "valeur": [3.1, 3.5]}))
    assert registry.fingerprint(store, "pib") != a                                   # une valeur change
    store.load_dataframe("pib", pd.DataFrame({"annee": [2022, 2023], "val": [3.1, 3.4]}))
    assert registry.fingerprint(store, "pib") != a                                   # un nom de colonne change


@pytest.mark.parametrize("t", ["absente", "pib; DROP TABLE pib", "", '"pib"'])
def test_fingerprint_refuses_unknown_or_unsafe_names(env, t):
    with pytest.raises(registry.CertificationError):
        registry.fingerprint(env[1], t)


# ── cycle de vie de la pastille ─────────────────────────────────────────────

def test_certified_then_stale_when_data_changes(env):
    c, store, _ = env
    assert status(c)["status"] == "none"
    r = certify(c)
    assert r.status_code == 201 and "ne vérifie pas l'institution" in r.json()["disclaimer"]
    s = status(c)
    assert s["status"] == "certified" and s["certifier"] == "INSTAD" and "fingerprint" not in s
    store.load_dataframe("pib", pd.DataFrame({"annee": [2022, 2023, 2024], "valeur": [3.1, 3.4, 3.6]}))
    s = status(c)
    assert s["status"] == "stale" and "changé" in s["detail"]


def test_recertifying_replaces_the_badge_and_keeps_history(env):
    c, store, _ = env
    certify(c)
    store.load_dataframe("pib", pd.DataFrame({"annee": [2022], "valeur": [1.0]}))
    assert status(c)["status"] == "stale"
    certify(c, reference="Note 2026-15")
    assert status(c)["status"] == "certified" and status(c)["reference"] == "Note 2026-15"
    assert len(c.get("/certification/pib/history", headers=ADMIN).json()["history"]) == 2


def test_revocation_and_expiry(env):
    c, store, tmp = env
    cid = certify(c).json()["id"]
    assert c.post(f"/certification/{cid}/revoke", json={"reason": "Erreur de source"}, headers=ADMIN).status_code == 200
    s = status(c)
    assert s["status"] == "revoked" and s["revoked_reason"] == "Erreur de source"
    # expiration : on antidate valid_until et on re-signe pour isoler le cas
    certify(c)
    items = json.loads((tmp / "certs.json").read_text())
    items[-1]["valid_until"] = (datetime.now(tz=timezone.utc) - timedelta(days=1)).isoformat()
    items[-1]["signature"] = registry._sign(registry._payload(items[-1]))
    (tmp / "certs.json").write_text(json.dumps(items))
    assert status(c)["status"] == "expired"


def test_edited_registry_file_is_detected(env):
    c, _, tmp = env
    certify(c)
    items = json.loads((tmp / "certs.json").read_text())
    items[0]["certifier"] = "Ministère des Finances"                                 # usurpation de l'institution
    (tmp / "certs.json").write_text(json.dumps(items))
    assert status(c)["status"] == "tampered"


def test_other_tables_are_not_certified(env):
    c, *_ = env
    certify(c)
    by = {t["table"]: t["status"] for t in c.get("/certification", headers=VIEWER).json()["tables"]}
    assert by == {"brouillon": "none", "pib": "certified"}


# ── droits et validation ────────────────────────────────────────────────────

def test_only_admin_can_certify_or_revoke_or_see_history(env):
    c, *_ = env
    body = {"table": "pib", "certifier": "INSTAD", "reference": "x"}
    assert c.post("/certification", json=body).status_code == 401
    assert c.post("/certification", json=body, headers=EDITOR).status_code == 403
    assert c.post("/certification", json=body, headers=VIEWER).status_code == 403
    cid = certify(c).json()["id"]
    assert c.post(f"/certification/{cid}/revoke", json={"reason": "x"}, headers=EDITOR).status_code == 403
    assert c.get("/certification/pib/history", headers=VIEWER).status_code == 403
    assert c.get("/certification", headers=VIEWER).status_code == 200
    assert c.get("/certification").status_code == 401


@pytest.mark.parametrize("kw", [{"table": "inconnue"}, {"certifier": "  "}, {"reference": ""},
                                {"valid_until": "demain"}, {"valid_until": "2020-01-01T00:00:00+00:00"}])
def test_validation(env, kw):
    assert certify(env[0], **kw).status_code == 422


def test_revoke_errors(env):
    c, *_ = env
    assert c.post("/certification/inconnu/revoke", json={"reason": "x"}, headers=ADMIN).status_code == 404
    cid = certify(c).json()["id"]
    assert c.post(f"/certification/{cid}/revoke", json={"reason": " "}, headers=ADMIN).status_code == 422


def test_audit_and_permissions_of_registry(env):
    c, _, tmp = env
    cid = certify(c).json()["id"]
    c.post(f"/certification/{cid}/revoke", json={"reason": "r"}, headers=ADMIN)
    audit = (tmp / "audit.jsonl").read_text()
    assert "dataset_certified" in audit and "dataset_certification_revoked" in audit and "INSTAD" not in audit
    assert oct((tmp / "certs.json").stat().st_mode & 0o777) == "0o600"


def test_corrupt_registry_is_not_overwritten(env):
    c, _, tmp = env
    (tmp / "certs.json").write_text("{cassé")
    assert certify(c).status_code == 422
    assert (tmp / "certs.json").read_text() == "{cassé"
    assert c.get("/certification", headers=VIEWER).status_code == 500


def test_protected_table_can_be_certified_without_leaking_rows(env, monkeypatch):
    import yaml
    c, store, tmp = env
    (tmp / "pol.yaml").write_text(yaml.safe_dump({"policies": [{"table": "pib", "column": "annee", "scope": "annee"}]}))
    monkeypatch.setenv("SOVEREIGN_ROW_POLICIES", str(tmp / "pol.yaml"))
    assert certify(c).status_code == 201
    assert "2023" not in json.dumps(status(c))

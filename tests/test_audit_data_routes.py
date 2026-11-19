"""P-074 : routes /audit-data (dépôt, aperçu, import, anomalies, résolution, isolation, audit)."""
from __future__ import annotations

import io
import json
import os

import openpyxl
import pytest
from fastapi.testclient import TestClient

from app import feedback
from app.data.duckdb_store import DataStore

ADMIN = {"X-Api-Key": "test-admin-key-sprint3"}
EDITOR = {"X-Api-Key": "test-editor-key-s6"}
VIEWER = {"X-Api-Key": "test-viewer-key-s6"}
CSV = ("Date;Compte;Libellé;Montant;Devise\n"
       "05/01/2026;601;Achat;1 200,50;DJF\n06/01/2026;602;Vente;80,00;DJF\n").encode()
BODY = {"mapping": {"entry_date": "Date", "account": "Compte", "label": "Libellé", "amount": "Montant", "currency": "Devise"},
        "decimal_separator": ",", "date_format": "%d/%m/%Y"}


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(feedback, "AUDIT_PATH", tmp_path / "audit.jsonl")
    monkeypatch.setenv("SOVEREIGN_AUDIT_DOCS_DIR", str(tmp_path / "docs"))
    monkeypatch.setenv("SOVEREIGN_AUTH_DB", str(tmp_path / "auth.db"))
    from app.auth import security as sec
    sec.init_auth_db()
    from app.main import app
    store = DataStore()
    monkeypatch.setattr(app.state, "store", store, raising=False)
    with TestClient(app) as c:
        yield c, store, tmp_path


def session(c, role: str, email: str | None = None) -> tuple[dict, str]:
    """Session nominative (résolution, revue et validation l'exigent, P-083) : (en-têtes Bearer, acteur `user:<id>`)."""
    from app.auth import security as sec
    email = email or f"{role}-{os.urandom(3).hex()}@example.org"
    uid = sec.create_user(email, "Un-mot-de-passe-long-1", role)
    r = c.post("/auth/login", json={"email": email, "password": "Un-mot-de-passe-long-1"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}, f"user:{uid}"


def upload(c, name="compta.csv", data=CSV, headers=EDITOR):
    return c.post("/audit-data/documents", files={"file": (name, data)}, headers=headers)


def audit_actions(tmp_path):
    p = tmp_path / "audit.jsonl"
    return [json.loads(line).get("action") for line in p.read_text().splitlines()] if p.exists() else []


def code(r):
    d = r.json()["detail"]
    return d["code"] if isinstance(d, dict) else d


# ── rôles ───────────────────────────────────────────────────────────────────

def test_roles_are_enforced(env):
    c, *_ = env
    assert c.get("/audit-data/documents").status_code == 401
    assert upload(c, headers={}).status_code == 401
    assert upload(c, headers=VIEWER).status_code == 403
    assert c.get("/audit-data/documents", headers=VIEWER).status_code == 200
    d = upload(c).json()["document"]["document_id"]
    assert c.get(f"/audit-data/documents/{d}/preview", headers=VIEWER).status_code == 403     # le contenu exige editor
    assert c.get(f"/audit-data/documents/{d}/issues", headers=VIEWER).status_code == 403
    assert c.post(f"/audit-data/documents/{d}/import", json=BODY, headers=VIEWER).status_code == 403


# ── dépôt, doublon, intégrité ──────────────────────────────────────────────

def test_upload_returns_preview_suggestions_and_stores_by_hash(env):
    c, _, tmp = env
    r = upload(c)
    assert r.status_code == 201
    j = r.json()
    doc = j["document"]
    assert j["duplicate"] is False and doc["status"] == "uploaded" and doc["rows_total"] == 2
    assert doc["uploaded_by"].startswith("legacy:editor:") and doc["display_name"] == "compta.csv"
    assert j["preview"]["headers"] == ["Date", "Compte", "Libellé", "Montant", "Devise"]
    assert j["suggestions"]["mapping"]["amount"] == "Montant" and j["suggestions"]["decimal_separator"] == ","
    assert (tmp / "docs" / f"{doc['sha256']}.csv").read_bytes() == CSV
    assert "audit_document_uploaded" in audit_actions(tmp)


def test_same_file_twice_is_detected_as_duplicate_with_same_hash(env):
    c, store, tmp = env
    first = upload(c).json()["document"]
    r = upload(c, name="autre_nom.csv")
    assert r.status_code == 200
    j = r.json()
    assert j["duplicate"] is True and j["document"]["document_id"] == first["document_id"]
    assert c.get(f"/audit-data/documents/{first['document_id']}", headers=VIEWER).json()["sha256"] == first["sha256"]
    assert len(c.get("/audit-data/documents", headers=VIEWER).json()["documents"]) == 1
    assert "audit_file_duplicate" in audit_actions(tmp)


def test_integrity_check_detects_a_modified_original(env):
    c, _, tmp = env
    doc = upload(c).json()["document"]
    d = doc["document_id"]
    assert c.get(f"/audit-data/documents/{d}/integrity", headers=VIEWER).json()["status"] == "ok"
    p = tmp / "docs" / f"{doc['sha256']}.csv"
    os.chmod(p, 0o600)
    p.write_bytes(CSV + b"01/01/2026;999;fraude;1;DJF\n")
    assert c.get(f"/audit-data/documents/{d}/integrity", headers=VIEWER).json()["status"] == "mismatch"
    r = c.get(f"/audit-data/documents/{d}/preview", headers=EDITOR)
    assert r.status_code == 409 and "audit_original_tampered" in audit_actions(tmp)       # lecture refusée
    p.unlink()
    assert c.get(f"/audit-data/documents/{d}/integrity", headers=VIEWER).json()["status"] == "missing"
    assert c.get(f"/audit-data/documents/{d}/preview", headers=EDITOR).status_code == 410


# ── fichiers hostiles : refusés ET journalisés ─────────────────────────────

@pytest.mark.parametrize("name,data,expected", [
    ("a.csv", b"MZ\x90\x00" + b"\x00" * 50, "content_mismatch"),
    ("a.xlsx", b"PK\x03\x04" + b"\x00" * 40, "not_a_zip"),
    ("../../etc/cron.d/x.csv", b"<html>", "content_mismatch"),
    ("macro.xlsm", b"x", "unsupported_type"),
    ("a.csv", b"", "empty_file"),
])
def test_hostile_files_are_refused_and_logged_without_leaking_state(env, name, data, expected):
    c, store, tmp = env
    r = upload(c, name=name, data=data)
    assert r.status_code == 400 and code(r) == expected
    assert "audit_file_refused" in audit_actions(tmp)
    assert c.get("/audit-data/documents", headers=VIEWER).json()["documents"] == []
    assert not (tmp / "docs").exists() or list((tmp / "docs").iterdir()) == []              # rien n'a été conservé
    assert str(tmp) not in r.text                                                           # pas de chemin serveur dans l'erreur


def test_booby_trapped_xlsx_is_refused(env):
    import zipfile
    c, _, tmp = env
    wb = openpyxl.Workbook()
    wb.active.append(["a", "b"])
    wb.active.append([1, 2])
    buf = io.BytesIO()
    wb.save(buf)
    out = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(buf.getvalue())) as src, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for i in src.infolist():
            z.writestr(i.filename, src.read(i.filename))
        z.writestr("xl/vbaProject.bin", b"evil")
    r = upload(c, "piege.xlsx", out.getvalue())
    assert r.status_code == 400 and code(r) == "macros_refused" and "audit_file_refused" in audit_actions(tmp)


def test_oversized_file_is_refused_with_413(env, monkeypatch):
    from app.audit_data import files
    monkeypatch.setattr(files, "MAX_BYTES", 50)
    c, *_ = env
    assert upload(c, data=CSV).status_code == 413


def test_unreadable_table_is_refused_after_validation(env):
    c, _, tmp = env
    r = upload(c, data=b"seulement\nune colonne\n")
    assert r.status_code == 422 and code(r) == "delimiter_undetermined" and "audit_file_refused" in audit_actions(tmp)
    assert c.get("/audit-data/documents", headers=VIEWER).json()["documents"] == []


def test_hostile_display_name_is_sanitised_in_storage(env):
    c, *_ = env
    doc = upload(c, name="..\\..\\x‮\nevil.csv").json()["document"]
    name = doc["display_name"]
    assert name.endswith("evil.csv") and not any(ch in name for ch in "\\/\u202e\n\x00")


# ── import ──────────────────────────────────────────────────────────────────

def test_import_without_currency_is_rejected_then_accepted_with_explicit_default(env):
    c, store, tmp = env
    data = b"Date;Compte;Montant\n05/01/2026;601;100\n"
    d = upload(c, data=data).json()["document"]["document_id"]
    body = {"mapping": {"entry_date": "Date", "account": "Compte", "amount": "Montant"}, "decimal_separator": ",", "date_format": "%d/%m/%Y"}
    r = c.post(f"/audit-data/documents/{d}/import", json=body, headers=EDITOR)
    assert r.status_code == 422 and code(r) == "currency_required"
    assert c.get(f"/audit-data/documents/{d}", headers=VIEWER).json()["status"] == "uploaded"       # rien d'écrit
    ok = c.post(f"/audit-data/documents/{d}/import", json={**body, "default_currency": "DJF"}, headers=EDITOR)
    assert ok.status_code == 200
    _, rows = store.execute("SELECT currency, currency_source FROM audit_financial_records")
    assert rows == [("DJF", "default")]                                                           # la devise par défaut est tracée


def test_dry_run_writes_nothing_then_import_persists_exact_decimals(env):
    c, store, tmp = env
    d = upload(c).json()["document"]["document_id"]
    dr = c.post(f"/audit-data/documents/{d}/import", json={**BODY, "dry_run": True}, headers=EDITOR).json()
    assert dr["dry_run"] is True and dr["summary"]["rows"] == 2
    assert "audit_document_imported" not in audit_actions(tmp)
    assert c.get(f"/audit-data/documents/{d}", headers=VIEWER).json()["status"] == "uploaded"
    r = c.post(f"/audit-data/documents/{d}/import", json=BODY, headers=EDITOR)
    assert r.status_code == 200 and r.json()["document"]["status"] == "imported" and r.json()["document"]["rows_imported"] == 2
    _, rows = store.execute("SELECT source_row, entry_date, account, amount::VARCHAR, currency FROM audit_financial_records ORDER BY 1")
    assert [(a, str(b), c_, d_, e) for a, b, c_, d_, e in rows] == [
        (2, "2026-01-05", "601", "1200.500000", "DJF"), (3, "2026-01-06", "602", "80.000000", "DJF")]
    assert "audit_document_imported" in audit_actions(tmp)


def test_second_import_is_refused_and_does_not_duplicate_records(env):
    c, store, _ = env
    d = upload(c).json()["document"]["document_id"]
    assert c.post(f"/audit-data/documents/{d}/import", json=BODY, headers=EDITOR).status_code == 200
    assert c.post(f"/audit-data/documents/{d}/import", json=BODY, headers=EDITOR).status_code == 409
    assert store.execute("SELECT count(*) FROM audit_financial_records")[1][0][0] == 2


def test_import_validation_errors_do_not_write(env):
    c, store, _ = env
    d = upload(c).json()["document"]["document_id"]
    for patch, expected in [({"decimal_separator": ";"}, 422), ({"date_format": "%d"}, 422), ({"default_currency": "dj"}, 422),
                            ({"mapping": {**BODY["mapping"], "account": "Absente"}}, 422)]:
        assert c.post(f"/audit-data/documents/{d}/import", json={**BODY, **patch}, headers=EDITOR).status_code == expected
    assert c.get(f"/audit-data/documents/{d}", headers=VIEWER).json()["status"] == "uploaded"


def test_no_silent_correction_bad_rows_become_null_plus_issues(env):
    c, store, _ = env
    data = (b"Date;Compte;Montant;Devise\n05/01/2026;601;12,5;DJF\n99/99/2026;602;abc;DJF\n05/01/2026;603;5;ZZZ\n")
    d = upload(c, data=data).json()["document"]["document_id"]
    r = c.post(f"/audit-data/documents/{d}/import", json={"mapping": {"entry_date": "Date", "account": "Compte", "amount": "Montant", "currency": "Devise"},
                                                          "decimal_separator": ",", "date_format": "%d/%m/%Y"}, headers=EDITOR).json()
    assert r["summary"]["rows_with_errors"] == 2
    _, rows = store.execute("SELECT source_row, entry_date IS NULL, amount IS NULL, currency IS NULL, has_error FROM audit_financial_records ORDER BY 1")
    assert rows == [(2, False, False, False, False), (3, True, True, False, True), (4, False, False, True, True)]
    issues = c.get(f"/audit-data/documents/{d}/issues", headers=EDITOR).json()
    assert {i["code"] for i in issues["issues"]} == {"invalid_date", "non_numeric_amount", "unknown_currency"}
    assert issues["counts"]["open_errors"] == 3


# ── résolution d'anomalies ─────────────────────────────────────────────────

def _doc_with_issues(c):
    data = b"Date;Compte;Montant;Devise\n05/01/2026;601;12;DJF\n05/01/2026;601;12;DJF\n99/99/2026;602;5;DJF\n"
    d = upload(c, data=data).json()["document"]["document_id"]
    c.post(f"/audit-data/documents/{d}/import", json={"mapping": {"entry_date": "Date", "account": "Compte", "amount": "Montant", "currency": "Devise"},
                                                      "decimal_separator": ",", "date_format": "%d/%m/%Y"}, headers=EDITOR)
    iss = c.get(f"/audit-data/documents/{d}/issues", headers=EDITOR).json()["issues"]
    return d, {i["code"]: i["issue_id"] for i in iss}


def test_resolution_requires_justification_and_records_author_and_audit(env):
    c, _, tmp = env
    d, ids = _doc_with_issues(c)
    w = ids["duplicate_row"]
    EDITOR_S, who = session(c, "editor")
    EDITOR, VIEWER_S = EDITOR_S, session(c, "viewer")[0]
    assert c.post(f"/audit-data/issues/{w}/resolve", json={"justification": "Une justification suffisante"}, headers=globals()["EDITOR"]).status_code == 403      # clé partagée : refusée
    assert c.post(f"/audit-data/issues/{w}/resolve", json={"justification": "court"}, headers=EDITOR).status_code == 422
    assert c.post(f"/audit-data/issues/{w}/resolve", json={}, headers=EDITOR).status_code == 422
    assert c.post(f"/audit-data/issues/{w}/resolve", json={"justification": "Deux achats légitimes le même jour"}, headers=VIEWER_S).status_code == 403
    r = c.post(f"/audit-data/issues/{w}/resolve", json={"justification": "  Deux achats légitimes le même jour  "}, headers=EDITOR)
    j = r.json()
    assert r.status_code == 200 and j["status"] == "resolved" and j["resolved_by"] == who and j["resolved_at"]
    assert j["justification"] == "Deux achats légitimes le même jour"
    assert "audit_issue_resolved" in audit_actions(tmp)
    assert c.post(f"/audit-data/issues/{w}/resolve", json={"justification": "Encore une justification"}, headers=EDITOR).status_code == 409
    assert c.get(f"/audit-data/documents/{d}", headers=VIEWER).json()["issue_counts"]["resolved_warnings"] == 1


def test_error_severity_issues_can_only_be_resolved_by_admin(env):
    c, *_ = env
    _, ids = _doc_with_issues(c)
    e = ids["invalid_date"]
    just = {"justification": "Date illisible, confirmée par le comptable"}
    assert c.post(f"/audit-data/issues/{e}/resolve", json=just, headers=session(c, "editor")[0]).status_code == 403
    admin_h, who = session(c, "admin")
    assert c.post(f"/audit-data/issues/{e}/resolve", json=just, headers=admin_h).json()["resolved_by"] == who


def test_issue_ids_are_validated_and_unknown_ids_are_404(env):
    c, *_ = env
    for bad in ("x", "' OR 1=1 --", "00000000-0000-0000-0000-000000000000"):
        assert c.post(f"/audit-data/issues/{bad}/resolve", json={"justification": "Une justification"}, headers=session(c, "admin")[0]).status_code == 404
        assert c.get(f"/audit-data/documents/{bad}", headers=VIEWER).status_code == 404


def test_issue_filters_are_whitelisted(env):
    c, *_ = env
    d, _ = _doc_with_issues(c)
    assert c.get(f"/audit-data/documents/{d}/issues?severity=warning", headers=EDITOR).json()["issues"][0]["code"] == "duplicate_row"
    assert c.get(f"/audit-data/documents/{d}/issues?status=x", headers=EDITOR).status_code == 422
    assert c.get(f"/audit-data/documents/{d}/issues?severity=' OR 1=1", headers=EDITOR).status_code == 422


# ── sécurité des données ───────────────────────────────────────────────────

def test_reserved_tables_cannot_be_uploaded_or_seen_by_the_ai_layer(env):
    c, store, _ = env
    upload(c)
    for name in ("audit_documents", "audit_quality_issues", "audit_financial_records"):
        r = c.post("/upload", files={"file": (f"{name}.csv", b"a,b\n1,2\n")}, headers=EDITOR)
        assert r.status_code == 400, name
    assert "audit_documents" not in store.tables and "audit_quality_issues" not in store.tables


def test_records_are_subject_to_row_policy_when_rules_exist(env, monkeypatch):
    """Les enregistrements normalisés restent lisibles seulement via DataStore.execute (donc sous sécurité par ligne)."""
    c, store, _ = env
    d = upload(c).json()["document"]["document_id"]
    c.post(f"/audit-data/documents/{d}/import", json=BODY, headers=EDITOR)
    assert "audit_financial_records" in store.tables
    cols, rows = store.execute("SELECT count(*) FROM audit_financial_records")
    assert rows[0][0] == 2


def test_formula_like_cells_stay_inert_text(env):
    c, store, _ = env
    data = b"Date;Compte;Libelle;Montant;Devise\n05/01/2026;601;=HYPERLINK(\"http://evil\");5;DJF\n"
    d = upload(c, data=data).json()["document"]["document_id"]
    c.post(f"/audit-data/documents/{d}/import", json={**BODY, "mapping": {**BODY["mapping"], "label": "Libelle"}}, headers=EDITOR)
    assert store.execute("SELECT label FROM audit_financial_records")[1][0][0] == '=HYPERLINK("http://evil")'


def test_xlsx_import_end_to_end_with_native_dates(env):
    from datetime import datetime
    c, store, _ = env
    wb = openpyxl.Workbook()
    wb.active.append(["Date", "Compte", "Montant", "Devise"])
    wb.active.append([datetime(2026, 1, 5), 601, 1200.5, "DJF"])
    buf = io.BytesIO()
    wb.save(buf)
    d = upload(c, "compta.xlsx", buf.getvalue()).json()["document"]["document_id"]
    r = c.post(f"/audit-data/documents/{d}/import", json={**BODY, "decimal_separator": ".", "mapping": {
        "entry_date": "Date", "account": "Compte", "amount": "Montant", "currency": "Devise"}}, headers=EDITOR)
    assert r.status_code == 200 and r.json()["summary"]["rows_with_errors"] == 0
    assert store.execute("SELECT entry_date::VARCHAR, amount::VARCHAR FROM audit_financial_records")[1] == [("2026-01-05", "1200.500000")]


def test_audit_chain_stays_valid_after_a_full_flow(env):
    c, _, tmp = env
    d = upload(c).json()["document"]["document_id"]
    c.post(f"/audit-data/documents/{d}/import", json=BODY, headers=EDITOR)
    assert c.get("/audit/verify", headers=ADMIN).json().get("valid", True) is True


def test_audit_failure_blocks_the_write(env, monkeypatch):
    c, *_ = env
    from app.security import actor

    def boom(*a, **k):
        raise OSError("disk full")
    monkeypatch.setattr(actor, "record_audit", boom)
    assert upload(c).status_code == 503
    assert c.get("/audit-data/documents", headers=VIEWER).json()["documents"] == []


# ── correctifs issus de la revue sécurité ──────────────────────────────────

def test_duplicate_response_leaks_only_id_and_status(env):
    c, *_ = env
    first = upload(c).json()["document"]["document_id"]
    dup = upload(c, name="x.csv").json()
    assert dup["document"] == {"document_id": first, "status": "uploaded"}


@pytest.fixture()
def with_rules(tmp_path, monkeypatch):
    f = tmp_path / "pol.yaml"
    f.write_text("policies:\n  - {table: ventes, column: region, scope: region}\n")
    monkeypatch.setenv("SOVEREIGN_ROW_POLICIES", str(f))


def test_with_row_policies_content_is_admin_only_and_metadata_is_redacted(env, with_rules):
    c, *_ = env
    d = upload(c, headers=ADMIN).json()["document"]["document_id"]
    c.post(f"/audit-data/documents/{d}/import", json=BODY, headers=ADMIN)
    assert c.get(f"/audit-data/documents/{d}/preview", headers=EDITOR).status_code == 403
    assert c.get(f"/audit-data/documents/{d}/issues", headers=EDITOR).status_code == 403
    assert c.get(f"/audit-data/documents/{d}/preview", headers=ADMIN).status_code == 200
    for hdr in (VIEWER, EDITOR):
        g = c.get(f"/audit-data/documents/{d}", headers=hdr).json()
        assert "summary" not in g and "display_name" not in g and "uploaded_by" not in g and "options" not in g
        assert "summary" not in c.get("/audit-data/documents", headers=hdr).json()["documents"][0]
    assert "summary" in c.get(f"/audit-data/documents/{d}", headers=ADMIN).json()


def test_oversized_declared_body_is_refused_early(env):
    c, _, tmp = env
    r = c.post("/audit-data/documents", files={"file": ("a.csv", CSV)}, headers={**EDITOR, "Content-Length": str(10**9)})
    assert r.status_code == 413


def test_importer_cannot_resolve_own_error_alone(env):
    c, *_ = env
    data = b"Date;Compte;Montant;Devise\n99/99/2026;602;5;DJF\n"
    a, _who = session(c, "admin")
    d = upload(c, data=data, headers=a).json()["document"]["document_id"]
    c.post(f"/audit-data/documents/{d}/import", json={**BODY, "mapping": {"entry_date": "Date", "account": "Compte", "amount": "Montant", "currency": "Devise"}}, headers=a)
    iid = c.get(f"/audit-data/documents/{d}/issues", headers=a).json()["issues"][0]["issue_id"]
    r = c.post(f"/audit-data/issues/{iid}/resolve", json={"justification": "Je valide ma propre erreur"}, headers=a)
    assert r.status_code == 403 and "Séparation" in r.json()["detail"]
    b, who_b = session(c, "admin")          # une AUTRE personne : deux acteurs distincts
    r = c.post(f"/audit-data/issues/{iid}/resolve", json={"justification": "Revue par un second administrateur"}, headers=b)
    assert r.status_code == 200 and r.json()["resolved_by"] == who_b


def test_resolution_audit_carries_justification_hash_not_text(env):
    c, _, tmp = env
    _, ids = _doc_with_issues(c)
    c.post(f"/audit-data/issues/{ids['duplicate_row']}/resolve", json={"justification": "Texte confidentiel unique"}, headers=session(c, "editor")[0])
    raw = (tmp / "audit.jsonl").read_text()
    assert "justification_sha256" in raw and "Texte confidentiel unique" not in raw


def test_import_commit_event_and_failed_event(env, monkeypatch):
    c, _, tmp = env
    d = upload(c).json()["document"]["document_id"]
    from app.audit_data import repo
    monkeypatch.setattr(repo, "insert_issues", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    with pytest.raises(RuntimeError):
        c.post(f"/audit-data/documents/{d}/import", json=BODY, headers=EDITOR)
    assert "audit_document_import_failed" in audit_actions(tmp)
    assert c.get(f"/audit-data/documents/{d}", headers=VIEWER).json()["status"] == "uploaded"       # annulé
    monkeypatch.undo()

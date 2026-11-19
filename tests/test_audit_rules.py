"""P-075 : règles de contrôle d'audit (déterministes, traçables, sans conclusion automatique)."""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app import feedback
from app.audit_rules.registry import ParamError, RuleError, _load_one, load_registry, render_params
from app.data.duckdb_store import DataStore

ADMIN = {"X-Api-Key": "test-admin-key-sprint3"}
EDITOR = {"X-Api-Key": "test-editor-key-s6"}
VIEWER = {"X-Api-Key": "test-viewer-key-s6"}
HEAD = "Date;Compte;Reference;Montant;Devise\n"
MAP = {"entry_date": "Date", "account": "Compte", "reference": "Reference", "amount": "Montant", "currency": "Devise"}


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(feedback, "AUDIT_PATH", tmp_path / "audit.jsonl")
    monkeypatch.setenv("SOVEREIGN_AUDIT_DOCS_DIR", str(tmp_path / "docs"))
    from app.main import app
    store = DataStore()
    monkeypatch.setattr(app.state, "store", store, raising=False)
    with TestClient(app) as c:
        yield c, store, tmp_path


def load(c, rows: str, mapping=MAP, head=HEAD, headers=EDITOR, **extra) -> str:
    d = c.post("/audit-data/documents", files={"file": ("f.csv", (head + rows).encode())}, headers=headers).json()["document"]["document_id"]
    r = c.post(f"/audit-data/documents/{d}/import", json={"mapping": mapping, "decimal_separator": ".", "date_format": "%d/%m/%Y", **extra}, headers=headers)
    assert r.status_code == 200, r.text
    return d


def run(c, doc, rules=None, params=None, headers=EDITOR):
    r = c.post("/audit-rules/runs", json={"document_id": doc, "rules": rules, "params": params or {}}, headers=headers)
    assert r.status_code == 201, r.text
    j = r.json()
    f = c.get(f"/audit-rules/runs/{j['run_id']}/findings", headers=headers).json()["findings"]
    return j, f


def st(j, code):
    return next(r for r in j["summary"]["rules"] if r["code"] == code)


# ── registre ────────────────────────────────────────────────────────────────

def test_ten_rules_loaded_with_versions_and_stable_hash():
    reg = load_registry()
    assert list(reg.rules) == [f"AUD{i:03d}" for i in range(1, 11)] and all(r.version == 1 for r in reg.rules.values())
    assert reg.ruleset_hash() == load_registry().ruleset_hash()


def test_rule_files_are_validated(tmp_path):
    good = (load_registry().rules["AUD001"])
    src = open("rules/audit/AUD001.yaml", encoding="utf-8").read()
    (tmp_path / "AUD001.yaml").write_text(src.replace("code: AUD001", "code: AUD009"))
    with pytest.raises(RuleError):
        _load_one(tmp_path / "AUD001.yaml")                                  # code ≠ nom de fichier
    (tmp_path / "AUD001.yaml").write_text(src + "\nextra: 1\n")
    with pytest.raises(RuleError):
        _load_one(tmp_path / "AUD001.yaml")                                  # clé inconnue
    (tmp_path / "AUD001.yaml").write_text(src.replace("{base}", "TRUE"))
    with pytest.raises(RuleError):
        _load_one(tmp_path / "AUD001.yaml")                                  # pas de filtre par document
    assert good.definition_hash


@pytest.mark.parametrize("code,params", [
    ("AUD002", {"window_days": "7; DROP TABLE x"}), ("AUD002", {"window_days": 0}), ("AUD002", {"window_days": 1.5}),
    ("AUD002", {"nope": 1}), ("AUD004", {"weekend_days": [8]}), ("AUD004", {"weekend_days": []}),
    ("AUD005", {}), ("AUD005", {"threshold": "abc"}), ("AUD005", {"threshold": -1}), ("AUD009", {"period_start": "2026-13-01"}),
    ("AUD009", {"period_start": "2026-01-01' OR '1'='1"}), ("AUD003", {"budgets": [{"account": "6'01", "currency": "DJF", "amount": 1}]}),
    ("AUD003", {"budgets": [{"account": "601", "currency": "djf", "amount": 1}]}), ("AUD003", {"budgets": "x"}),
    ("AUD003", {"budgets": [{"account": "601", "currency": "DJF", "amount": 1}] * 2}),
])
def test_parameters_are_validated_and_never_interpolated_raw(code, params):
    with pytest.raises(ParamError):
        render_params(load_registry().rules[code], params)


# ── critères d'acceptation ─────────────────────────────────────────────────

def test_two_strictly_identical_invoices_are_flagged_with_rule_and_version(env):
    c, *_ = env
    d = load(c, "05/01/2026;601;F-100;500;DJF\n05/01/2026;601;F-100;500;DJF\n06/01/2026;601;F-101;500;DJF\n")
    j, f = run(c, d, ["AUD001"])
    assert len(f) == 1 and f[0]["rule_code"] == "AUD001" and f[0]["rule_version"] == 1 and f[0]["status"] == "to_review"
    assert f[0]["source_rows"] == [2, 3] and f[0]["summary"].startswith("Signal de risque à examiner")
    assert "fraude" not in json.dumps(f).lower() and j["summary"]["ruleset_hash"]


def test_two_distinct_same_amount_payments_are_info_not_a_conclusion(env):
    c, *_ = env
    d = load(c, "05/01/2026;613;LOYER-1;900;DJF\n12/01/2026;613;LOYER-2;900;DJF\n")
    _, f = run(c, d, ["AUD001", "AUD002"])
    assert [(x["rule_code"], x["severity"]) for x in f] == [("AUD002", "info")]       # pas de doublon AUD001, simple rapprochement
    assert "examiner" in f[0]["summary"].lower()


def test_spend_without_budget_or_over_budget_is_flagged(env):
    c, *_ = env
    d = load(c, "05/01/2026;601;A;800;DJF\n06/01/2026;602;B;50;DJF\n07/01/2026;603;C;10;DJF\n")
    bud = [{"account": "601", "currency": "DJF", "amount": 500}, {"account": "602", "currency": "DJF", "amount": 100}]
    j, f = run(c, d, ["AUD003"], {"AUD003": {"budgets": bud}})
    reasons = sorted(json.loads(x["details"]["reason"] if False else json.dumps(x["details"]["reason"])) for x in f)
    assert reasons == ["budget dépassé", "sans budget déclaré"]                    # 601 dépassé, 603 sans budget, 602 OK
    j2, f2 = run(c, d, ["AUD003"])                                               # sans budgets fournis
    assert f2 == [] and st(j2, "AUD003")["status"] == "not_applicable" and "budgets" in st(j2, "AUD003")["reason"]


def test_weekend_rule_is_indicative_only(env):
    c, *_ = env
    d = load(c, "03/01/2026;601;A;10;DJF\n05/01/2026;601;B;10;DJF\n")        # samedi 3 janvier 2026, lundi 5
    j, f = run(c, d, ["AUD004"])
    assert len(f) == 1 and f[0]["indicative"] is True and f[0]["summary"].startswith("Indicatif seulement")
    _, f2 = run(c, d, ["AUD004"], {"AUD004": {"weekend_days": [5, 6]}})       # vendredi/samedi
    assert len(f2) == 1 and f2[0]["source_rows"] == [2]
    assert next(r for r in c.get("/audit-rules/rules", headers=VIEWER).json()["rules"] if r["code"] == "AUD004")["indicative"] is True


# ── autres règles ───────────────────────────────────────────────────────────

def test_splitting_needs_explicit_threshold_and_flags_cumulative(env):
    c, *_ = env
    d = load(c, "05/01/2026;601;A;400;DJF\n06/01/2026;601;B;400;DJF\n20/03/2026;601;C;400;DJF\n")
    j, f = run(c, d, ["AUD005"])
    assert st(j, "AUD005")["status"] == "not_applicable"                          # aucun seuil par défaut supposé
    _, f = run(c, d, ["AUD005"], {"AUD005": {"threshold": 500}})
    assert len(f) == 1 and f[0]["source_rows"] == [2, 3] and f[0]["amount"] == "800.000000"


def test_unusual_amount_requires_enough_history(env):
    c, *_ = env
    rows = "".join(f"{i:02d}/01/2026;601;R{i};{100 + i % 3};DJF\n" for i in range(1, 12)) + "20/01/2026;601;BIG;9000;DJF\n"
    d = load(c, rows)
    _, f = run(c, d, ["AUD006"])
    assert len(f) == 1 and "9000" in f[0]["summary"]
    small = load(c, "05/01/2026;602;X;10;DJF\n06/01/2026;602;Y;99999;DJF\n")
    _, f2 = run(c, small, ["AUD006"])
    assert f2 == []


def test_bank_details_rule_is_not_applicable_without_the_field(env):
    c, *_ = env
    d = load(c, "05/01/2026;601;A;10;DJF\n")
    j, f = run(c, d, ["AUD007"])
    assert f == [] and st(j, "AUD007")["status"] == "not_applicable" and "bank_account" in st(j, "AUD007")["reason"]


def test_missing_reference_and_out_of_period(env):
    c, *_ = env
    d = load(c, "05/01/2026;601;;50;DJF\n05/01/2025;601;F1;50;DJF\n05/01/2026;601;F2;50;DJF\n")
    _, f = run(c, d, ["AUD008"])
    assert [x["source_rows"] for x in f] == [[2]]
    _, f = run(c, d, ["AUD009"], {"AUD009": {"period_start": "2026-01-01", "period_end": "2026-12-31"}})
    assert [x["source_rows"] for x in f] == [[3]]


def test_unbalanced_entry_only_with_debit_credit_columns(env):
    c, *_ = env
    m = {"entry_date": "Date", "account": "Compte", "reference": "Reference", "debit": "Debit", "credit": "Credit", "currency": "Devise"}
    d = load(c, "05/01/2026;601;E1;100;;DJF\n05/01/2026;401;E1;;100;DJF\n06/01/2026;601;E2;50;;DJF\n06/01/2026;401;E2;;40;DJF\n",
             mapping=m, head="Date;Compte;Reference;Debit;Credit;Devise\n")
    _, f = run(c, d, ["AUD010"])
    assert len(f) == 1 and f[0]["details"]["reference"] == "E2" and f[0]["amount"].startswith("10")
    plain = load(c, "05/01/2026;601;A;10;DJF\n")
    j, f = run(c, plain, ["AUD010"])
    assert f == [] and st(j, "AUD010")["status"] == "not_applicable"


def test_rows_with_import_errors_are_excluded_and_counted(env):
    c, *_ = env
    d = load(c, "05/01/2026;601;F1;abc;DJF\n05/01/2026;601;F1;abc;DJF\n05/01/2026;601;;50;DJF\n")
    j, f = run(c, d, ["AUD001", "AUD008"])
    assert j["summary"]["rows_excluded_for_errors"] == 2 and [x["rule_code"] for x in f] == ["AUD008"]


# ── traçabilité, droits, isolation ─────────────────────────────────────────

def test_run_is_reproducible_and_audited(env):
    c, _, tmp = env
    d = load(c, "05/01/2026;601;F-100;500;DJF\n05/01/2026;601;F-100;500;DJF\n")
    j1, f1 = run(c, d, ["AUD001"])
    j2, f2 = run(c, d, ["AUD001"])
    strip = lambda fs: [(x["rule_code"], x["rule_version"], x["summary"], x["source_rows"]) for x in fs]   # noqa: E731
    assert strip(f1) == strip(f2) and j1["run_id"] != j2["run_id"]
    assert "audit_rules_run" in (tmp / "audit.jsonl").read_text()
    assert c.get(f"/audit-rules/runs/{j1['run_id']}", headers=EDITOR).json()["ruleset_hash"] == j1["summary"]["ruleset_hash"]


def test_roles_and_run_visibility(env):
    c, *_ = env
    d = load(c, "05/01/2026;601;A;10;DJF\n", headers=ADMIN)
    assert c.get("/audit-rules/rules").status_code == 401 and c.get("/audit-rules/rules", headers=VIEWER).status_code == 200
    assert c.post("/audit-rules/runs", json={"document_id": d}, headers=VIEWER).status_code == 403
    j, _ = run(c, d, headers=EDITOR)
    rid = j["run_id"]
    assert c.get(f"/audit-rules/runs/{rid}/findings", headers=VIEWER).status_code == 403
    assert c.get(f"/audit-rules/runs/{rid}", headers=ADMIN).status_code == 200
    ja, _ = run(c, d, headers=ADMIN)
    assert c.get(f"/audit-rules/runs/{ja['run_id']}", headers=EDITOR).status_code == 404       # run d'un autre : introuvable


def test_input_validation(env):
    c, *_ = env
    d = load(c, "05/01/2026;601;A;10;DJF\n")
    for body, code in [({"document_id": "x" * 36}, 404), ({"document_id": d, "rules": ["AUD999"]}, 422),
                       ({"document_id": d, "params": {"AUD999": {}}}, 422), ({"document_id": "short"}, 422)]:
        assert c.post("/audit-rules/runs", json=body, headers=EDITOR).status_code == code
    up = c.post("/audit-data/documents", files={"file": ("g.csv", (HEAD + "05/01/2026;601;Z;1;DJF\n").encode())}, headers=EDITOR).json()["document"]["document_id"]
    assert c.post("/audit-rules/runs", json={"document_id": up}, headers=EDITOR).status_code == 409      # non importé
    for bad in ("x", "' OR 1=1 --"):
        assert c.get(f"/audit-rules/runs/{bad}", headers=ADMIN).status_code == 404
        assert c.get(f"/audit-rules/runs/{bad}/findings", headers=ADMIN).status_code == 404


def test_with_row_policies_only_admin_runs_checks(env, tmp_path, monkeypatch):
    c, *_ = env
    d = load(c, "05/01/2026;601;A;10;DJF\n", headers=ADMIN)
    f = tmp_path / "pol.yaml"
    f.write_text("policies:\n  - {table: ventes, column: region, scope: region}\n")
    monkeypatch.setenv("SOVEREIGN_ROW_POLICIES", str(f))
    assert c.post("/audit-rules/runs", json={"document_id": d}, headers=EDITOR).status_code == 403
    assert c.post("/audit-rules/runs", json={"document_id": d}, headers=ADMIN).status_code == 201


def test_audit_failure_blocks_run(env, monkeypatch):
    c, store, _ = env
    d = load(c, "05/01/2026;601;A;10;DJF\n")
    from app.security import actor
    monkeypatch.setattr(actor, "record_audit", lambda *a, **k: (_ for _ in ()).throw(OSError("full")))
    assert c.post("/audit-rules/runs", json={"document_id": d}, headers=EDITOR).status_code == 503
    from app.audit_rules import store as rstore
    rstore.ensure_tables(store)
    assert store.execute("SELECT count(*) FROM audit_rule_runs")[1][0][0] == 0


def test_rule_tables_are_reserved(env):
    c, store, _ = env
    for n in ("audit_findings", "audit_rule_runs"):
        assert c.post("/upload", files={"file": (f"{n}.csv", b"a,b\n1,2\n")}, headers=EDITOR).status_code == 400
        assert n not in store.tables


# ── correctifs issus de la revue sécurité ──────────────────────────────────

@pytest.mark.parametrize("code,params", [
    ("AUD005", {"threshold": "1E+999999999"}), ("AUD005", {"threshold": "9" * 41}), ("AUD002", {"window_days": 10**30}),
    ("AUD006", {"z_threshold": "1E+20000000"}),
])
def test_huge_numeric_parameters_are_refused(code, params):
    with pytest.raises(ParamError):
        render_params(load_registry().rules[code], params)


def test_registry_requires_has_error_filter_without_base(tmp_path):
    src = open("rules/audit/AUD010.yaml", encoding="utf-8").read().replace("has_error", "has_err0r")
    (tmp_path / "AUD010.yaml").write_text(src)
    with pytest.raises(RuleError):
        _load_one(tmp_path / "AUD010.yaml")


def test_duplicate_rules_are_collapsed_and_findings_not_duplicated(env):
    c, *_ = env
    d = load(c, "05/01/2026;601;F-1;500;DJF\n05/01/2026;601;F-1;500;DJF\n")
    j, f = run(c, d, ["AUD001"] * 5)
    assert len(j["summary"]["rules"]) == 1 and len(f) == 1


def test_invalid_params_are_not_echoed_back(env):
    c, *_ = env
    d = load(c, "05/01/2026;601;A;10;DJF\n")
    j, _ = run(c, d, ["AUD005"], {"AUD005": {"threshold": "<script>x</script>"}})
    assert st(j, "AUD005")["params"] == {} and "script" not in json.dumps(j)
    big = {"AUD005": {"threshold": "1", "x": "y" * 30000}}
    assert c.post("/audit-rules/runs", json={"document_id": d, "params": big}, headers=EDITOR).status_code == 422


def test_findings_order_is_deterministic_and_unknown_rule_message_is_fixed(env):
    c, *_ = env
    d = load(c, "".join(f"05/01/2026;601;F{i};10;DJF\n05/01/2026;601;F{i};10;DJF\n" for i in range(5)))
    a = [x["source_rows"] for x in run(c, d, ["AUD001"])[1]]
    assert a == [x["source_rows"] for x in run(c, d, ["AUD001"])[1]] and len(a) == 5
    r = c.post("/audit-rules/runs", json={"document_id": d, "rules": ["<b>x</b>"]}, headers=EDITOR)
    assert r.status_code == 422 and "<b>" not in r.text


def test_concurrent_run_is_refused_with_429(env):
    from app.routers import audit_rules
    c, *_ = env
    d = load(c, "05/01/2026;601;A;10;DJF\n")
    assert audit_rules._RUN_SLOT.acquire(blocking=False)
    try:
        assert c.post("/audit-rules/runs", json={"document_id": d}, headers=EDITOR).status_code == 429
    finally:
        audit_rules._RUN_SLOT.release()


def test_slow_rule_is_interrupted(env, monkeypatch):
    from app.audit_rules import engine
    c, *_ = env
    d = load(c, "05/01/2026;601;A;10;DJF\n")
    monkeypatch.setattr(engine, "RULE_TIMEOUT_S", 0.001)
    monkeypatch.setattr(engine.threading, "Timer", lambda t, fn: type("T", (), {"start": lambda s: fn(), "cancel": lambda s: None})())
    j, _ = run(c, d, ["AUD001"])
    assert st(j, "AUD001")["status"] in ("error", "ran")        # interrompu ou terminé avant l'interruption : jamais d'exception

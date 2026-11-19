"""P-073 : routes /financial (formules, analyses reproductibles, lecture sécurisée des données)."""
from __future__ import annotations

import json

import pandas as pd
import pytest
import yaml
from fastapi.testclient import TestClient

from app import feedback
from app.data.duckdb_store import DataStore

ADMIN = {"X-Api-Key": "test-admin-key-sprint3"}
EDITOR = {"X-Api-Key": "test-editor-key-s6"}
VIEWER = {"X-Api-Key": "test-viewer-key-s6"}
BUD = {"formula_code": "BUD001", "inputs": {"budget_vote": "120000000", "depenses": "114000000"}}


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(feedback, "AUDIT_PATH", tmp_path / "audit.jsonl")
    from app.main import app
    store = DataStore()
    monkeypatch.setattr(app.state, "store", store, raising=False)
    with TestClient(app) as c:
        yield c, store, tmp_path


def post(c, body=BUD, headers=EDITOR):
    return c.post("/financial/runs", json=body, headers=headers)


# ── formules ────────────────────────────────────────────────────────────────

def test_list_and_read_formulas(env):
    c, *_ = env
    r = c.get("/financial/formulas", headers=VIEWER).json()
    assert len(r["formulas"]) == 11 and r["engine_version"]
    assert c.get("/financial/formulas?family=recettes", headers=VIEWER).json()["formulas"][0]["code"].startswith("REC")
    f = c.get("/financial/formulas/BUD001", headers=VIEWER).json()
    assert f["versions"][0]["expression"] == "depenses / budget_vote * 100"
    assert c.get("/financial/formulas/BUD001?version=1", headers=VIEWER).json()["version"] == 1
    assert c.get("/financial/formulas/NOPE", headers=VIEWER).status_code == 404
    assert c.get("/financial/formulas/BUD001?version=9", headers=VIEWER).status_code == 404


def test_roles_are_enforced(env):
    c, *_ = env
    assert c.get("/financial/formulas").status_code == 401
    assert post(c, headers={}).status_code == 401
    assert post(c, headers=VIEWER).status_code == 403          # lancer un calcul exige editor
    assert c.get("/financial/runs", headers=VIEWER).status_code == 200
    assert post(c, headers=EDITOR).status_code == 201 and post(c, headers=ADMIN).status_code == 201


# ── calcul et reproductibilité ──────────────────────────────────────────────

def test_reference_run_is_returned_with_full_traceability(env):
    c, *_ = env
    r = post(c).json()
    assert r["result"]["value"] == "95.00" and r["result"]["unit"] == "%" and r["status"] == "ok"
    assert r["formula_code"] == "BUD001" and r["formula_version"] == 1 and r["engine_version"]
    assert all(r[k] for k in ("definition_hash", "input_snapshot_hash", "result_hash", "ruleset_version"))
    assert r["inputs"] == {"budget_vote": "120000000", "depenses": "114000000"}
    assert r["definition_status"] == "unchanged" and r["created_by"].startswith("legacy:editor:")


def test_same_analysis_same_parameters_same_result_and_hash(env):
    c, *_ = env
    a, b = post(c).json(), post(c).json()
    assert a["run_id"] != b["run_id"]
    assert (a["result_hash"], a["input_snapshot_hash"], a["result"]["value"]) == (b["result_hash"], b["input_snapshot_hash"], b["result"]["value"])
    cmp = c.get(f"/financial/runs/{a['run_id']}/compare/{b['run_id']}", headers=VIEWER).json()
    assert cmp["same_result_hash"] and cmp["same_inputs"] and cmp["delta_b_minus_a"] == "0"


def test_compare_shows_input_differences_and_delta(env):
    c, *_ = env
    a = post(c).json()
    b = post(c, {**BUD, "inputs": {"budget_vote": "120000000", "depenses": "120000000"}}).json()
    cmp = c.get(f"/financial/runs/{a['run_id']}/compare/{b['run_id']}", headers=VIEWER).json()
    assert not cmp["same_result_hash"] and cmp["input_differences"] == {"depenses": {"a": "114000000", "b": "120000000"}}
    assert cmp["value_a"] == "95.00" and cmp["value_b"] == "100.00" and cmp["delta_b_minus_a"] == "5"


def test_get_and_list_runs(env):
    c, *_ = env
    a = post(c).json()
    post(c, {"formula_code": "REC001", "inputs": {"recettes_prevues": "60", "recettes_encaissees": "54"}})
    assert c.get(f"/financial/runs/{a['run_id']}", headers=VIEWER).json()["result"]["value"] == "95.00"
    assert len(c.get("/financial/runs", headers=VIEWER).json()["runs"]) == 2
    only = c.get("/financial/runs?formula_code=REC001", headers=VIEWER).json()["runs"]
    assert [x["formula_code"] for x in only] == ["REC001"] and "inputs_json" not in only[0]
    assert c.get("/financial/runs?limit=0", headers=VIEWER).status_code == 422
    assert c.get("/financial/runs/not-a-uuid", headers=VIEWER).status_code == 404
    assert c.get("/financial/runs/00000000-0000-0000-0000-000000000000", headers=VIEWER).status_code == 404
    assert c.get("/financial/runs/x'%20OR%201=1%20--", headers=VIEWER).status_code == 404


# ── erreurs explicites, jamais silencieuses ─────────────────────────────────

@pytest.mark.parametrize("body,code", [
    ({"formula_code": "BUD001", "inputs": {"budget_vote": "0", "depenses": "5"}}, "division_by_zero"),
    ({"formula_code": "BUD001", "inputs": {"depenses": "5"}}, "missing_value"),
    ({"formula_code": "BUD001", "inputs": {"budget_vote": "-1", "depenses": "5"}}, "negative_value"),
    ({"formula_code": "BUD001", "inputs": {"budget_vote": "abc", "depenses": "5"}}, "invalid_value"),
    ({"formula_code": "BUD001", "inputs": {"budget_vote": "NaN", "depenses": "5"}}, "invalid_value"),
    ({"formula_code": "BUD001", "inputs": {"budget_vote": "1", "depenses": "5", "x": "1"}}, "unknown_variable"),
])
def test_rejections_are_422_with_a_code_and_are_not_stored(env, body, code):
    c, *_ = env
    r = post(c, body)
    assert r.status_code == 422 and r.json()["detail"]["code"] == code
    assert c.get("/financial/runs", headers=VIEWER).json()["runs"] == []


def test_unknown_formula_or_version_is_404_and_floats_are_refused(env):
    c, *_ = env
    assert post(c, {"formula_code": "NOPE", "inputs": {}}).status_code == 404
    assert post(c, {**BUD, "version": 7}).status_code == 404
    bad = post(c, {"formula_code": "BUD001", "inputs": {"budget_vote": 120.5, "depenses": "1"}})
    assert bad.status_code == 422                       # pas de flottant JSON : montants en chaînes
    assert post(c, {"formula_code": "BUD001", "inputs": {"budget_vote": 100, "depenses": 50}}).json()["result"]["value"] == "50.00"
    assert post(c, {"formula_code": "bud001", "inputs": {}}).status_code == 422


# ── versions : l'ancienne reste calculable, la modification en place est détectée ──

def _two_versions(tmp_path, monkeypatch, second=True):
    base = {"version": 1, "label": "T", "expression": "a / b", "precision": 2, "rounding": "ROUND_HALF_UP",
            "on_zero_division": "error", "variables": {"a": {}, "b": {}}}
    versions = [base] + ([{**base, "version": 2, "expression": "a / b * 100"}] if second else [])
    d = tmp_path / "formulas"
    d.mkdir(exist_ok=True)
    (d / "tst001.yaml").write_text(yaml.safe_dump({"code": "TST001", "versions": versions}))
    monkeypatch.setenv("SOVEREIGN_FORMULAS_DIR", str(d))
    return d


def test_new_version_does_not_change_old_runs_and_old_version_stays_usable(env, monkeypatch):
    c, _, tmp = env
    _two_versions(tmp, monkeypatch, second=False)
    inputs = {"a": "1", "b": "4"}
    old = post(c, {"formula_code": "TST001", "inputs": inputs}).json()
    assert old["formula_version"] == 1 and old["result"]["value"] == "0.25"
    _two_versions(tmp, monkeypatch, second=True)                       # on ajoute la v2
    latest = post(c, {"formula_code": "TST001", "inputs": inputs}).json()
    pinned = post(c, {"formula_code": "TST001", "version": 1, "inputs": inputs}).json()
    assert latest["formula_version"] == 2 and latest["result"]["value"] == "25.00"
    assert pinned["result"]["value"] == "0.25" and pinned["result_hash"] == old["result_hash"]
    assert c.get(f"/financial/runs/{old['run_id']}", headers=VIEWER).json()["definition_status"] == "unchanged"


def test_editing_a_version_in_place_is_flagged_on_old_runs(env, monkeypatch):
    c, _, tmp = env
    d = _two_versions(tmp, monkeypatch, second=False)
    run = post(c, {"formula_code": "TST001", "inputs": {"a": "1", "b": "4"}}).json()
    data = yaml.safe_load((d / "tst001.yaml").read_text())
    data["versions"][0]["expression"] = "a / b * 2"                    # modification interdite : pas de nouvelle version
    (d / "tst001.yaml").write_text(yaml.safe_dump(data))
    assert c.get(f"/financial/runs/{run['run_id']}", headers=VIEWER).json()["definition_status"] == "definition_changed"
    (d / "tst001.yaml").unlink()
    (d / "other.yaml").write_text(yaml.safe_dump({**data, "code": "OTHER", "versions": [data["versions"][0]]}))
    assert c.get(f"/financial/runs/{run['run_id']}", headers=VIEWER).json()["definition_status"] == "formula_missing"


# ── lecture de données par DataStore.execute ───────────────────────────────

def load(store):
    store.load_dataframe("budget_2026", pd.DataFrame({
        "ligne": ["a", "b", "c"], "vote": [60, 40, 20], "paye": [50.25, 30.5, 10.0],
        "note": ["x", "y", "z"], "vide": [None, None, None]}))
    store.con.execute("CREATE TABLE montants (m DECIMAL(18,2))")
    store.con.execute("INSERT INTO montants VALUES (0.10), (0.20)")
    store.tables.add("montants")


def test_from_table_sums_integer_decimal_and_float_columns_exactly(env):
    c, store, _ = env
    load(store)
    body = {"formula_code": "BUD001", "from_table": {
        "budget_vote": {"table": "budget_2026", "column": "vote"},
        "depenses": {"table": "budget_2026", "column": "paye"}}}
    r = post(c, body).json()
    assert r["inputs"] == {"budget_vote": "120", "depenses": "90.75"} and r["result"]["value"] == "75.63"
    assert r["sources"]["depenses"]["cast"] == "DECIMAL(38,6)"          # conversion flottant → décimal déclarée
    assert "cast" not in r["sources"]["budget_vote"]
    dec = post(c, {"formula_code": "BUD002", "from_table": {"depenses": {"table": "montants", "column": "m"}},
                   "inputs": {"budget_vote": "0"}}).json()
    assert dec["inputs"]["depenses"] == "0.3" and dec["result"]["value"] == "0.30"      # 0.1 + 0.2 exact


def test_from_table_refusals(env):
    c, store, _ = env
    load(store)
    def bind(**kw):
        return post(c, {"formula_code": "BUD001", "inputs": {"depenses": "1"}, "from_table": {"budget_vote": kw}})
    cases = [({"table": "inconnue", "column": "vote"}, "unknown_table"),
             ({"table": "budget_2026", "column": "nope"}, "unknown_column"),
             ({"table": "budget_2026", "column": "note"}, "unsupported_column"),     # texte
             ({"table": "budget_2026", "column": "vide"}, "missing_value"),           # somme nulle ≠ 0
             ({"table": "audit_analysis_runs", "column": "run_id"}, "unknown_table")]  # tables internes non liables
    for kw, code in cases:
        r = bind(**kw)
        assert r.status_code == 422 and r.json()["detail"]["code"] == code, (kw, r.text)


def test_from_table_rejects_sql_injection_in_identifiers(env):
    c, store, _ = env
    load(store)
    for bad in ('budget_2026" WHERE 1=1 --', "budget_2026; DROP TABLE montants", "a b", "x'y", ""):
        r = post(c, {"formula_code": "BUD001", "inputs": {"depenses": "1"},
                     "from_table": {"budget_vote": {"table": bad, "column": "vote"}}})
        assert r.status_code == 422, bad
    r = post(c, {"formula_code": "BUD001", "inputs": {"depenses": "1"},
                 "from_table": {"budget_vote": {"table": "budget_2026", "column": "vote", "agg": "avg; DROP"}}})
    assert r.status_code == 422
    assert "montants" in store.tables and store.con.execute("SELECT count(*) FROM montants").fetchone()[0] == 2


def test_variable_given_twice_is_refused(env):
    c, store, _ = env
    load(store)
    r = post(c, {"formula_code": "BUD001", "inputs": {"budget_vote": "1", "depenses": "1"},
                 "from_table": {"budget_vote": {"table": "budget_2026", "column": "vote"}}})
    assert r.status_code == 422 and r.json()["detail"]["code"] == "duplicate_source"


def test_row_security_applies_to_table_reads(env, monkeypatch):
    c, store, tmp = env
    load(store)
    (tmp / "pol.yaml").write_text(yaml.safe_dump({"policies": [{"table": "budget_2026", "column": "ligne", "scope": "ligne"}]}))
    monkeypatch.setenv("SOVEREIGN_ROW_POLICIES", str(tmp / "pol.yaml"))
    body = {"formula_code": "BUD001", "inputs": {"depenses": "1"},
            "from_table": {"budget_vote": {"table": "budget_2026", "column": "vote"}}}
    r = post(c, body, EDITOR)
    assert r.status_code == 403                          # clé API non admin : refus sur table protégée (échec fermé)
    assert c.get("/financial/runs", headers=VIEWER).json()["runs"] == []
    assert post(c, body, ADMIN).status_code == 201       # l'admin voit tout


# ── audit ───────────────────────────────────────────────────────────────────

def test_actions_are_audited_without_input_values(env):
    c, _, tmp = env
    run = post(c).json()
    post(c, {"formula_code": "BUD001", "inputs": {"budget_vote": "0", "depenses": "987654321"}})
    lines = [json.loads(x) for x in (tmp / "audit.jsonl").read_text().splitlines()]
    actions = [x["action"] for x in lines]
    assert "financial_run" in actions and "financial_run_rejected" in actions
    ok = next(x for x in lines if x["action"] == "financial_run")["details"]
    assert ok["run_id"] == run["run_id"] and ok["result_hash"] == run["result_hash"]
    raw = (tmp / "audit.jsonl").read_text()
    assert "987654321" not in raw and "114000000" not in raw        # aucune valeur de donnée dans le journal
    assert c.get("/audit/verify", headers=ADMIN).status_code == 200


# ── relecture sécurité : E1 visibilité des runs issus de tables ────────────

TABLE_RUN = {"formula_code": "BUD002", "inputs": {"budget_vote": "0"},
             "from_table": {"depenses": {"table": "budget_2026", "column": "vote"}}}


def test_runs_built_from_tables_are_visible_only_to_their_author_and_admin(env):
    c, store, _ = env
    load(store)
    secret = post(c, TABLE_RUN, EDITOR).json()
    plain = post(c).json()
    sid, pid = secret["run_id"], plain["run_id"]
    assert c.get(f"/financial/runs/{sid}", headers=VIEWER).status_code == 404       # même réponse qu'un run inexistant
    assert c.get(f"/financial/runs/{sid}", headers=EDITOR).status_code == 200      # l'auteur
    assert c.get(f"/financial/runs/{sid}", headers=ADMIN).status_code == 200       # l'admin voit tout
    assert c.get(f"/financial/runs/{pid}", headers=VIEWER).status_code == 200      # entrées explicites : lisible
    seen = [x["run_id"] for x in c.get("/financial/runs", headers=VIEWER).json()["runs"]]
    assert seen == [pid] and secret["run_id"] not in seen
    assert {x["run_id"] for x in c.get("/financial/runs", headers=ADMIN).json()["runs"]} == {sid, pid}
    assert c.get(f"/financial/runs/{sid}/compare/{pid}", headers=VIEWER).status_code == 404   # pas de fuite par la comparaison
    assert c.get(f"/financial/runs/{sid}/compare/{pid}", headers=ADMIN).status_code == 200


def test_run_visibility_follows_the_author_not_just_the_role(env):
    c, store, _ = env
    load(store)
    mine = post(c, TABLE_RUN, ADMIN).json()
    assert mine["created_by"].startswith("legacy:admin:")
    assert c.get(f"/financial/runs/{mine['run_id']}", headers=EDITOR).status_code == 404


# ── E2 : tables internes réservées ─────────────────────────────────────────

def test_history_tables_cannot_be_replaced_by_an_upload(env):
    c, store, _ = env
    run = post(c).json()
    for name in ("audit_analysis_runs", "audit_calculation_results"):
        r = c.post("/upload", files={"file": (f"{name}.csv", b"run_id,x\n1,2\n", "text/csv")}, headers=VIEWER)
        assert r.status_code == 400 and "réservé" in r.text, r.text
    assert c.get(f"/financial/runs/{run['run_id']}", headers=VIEWER).json()["integrity"] == "ok"
    with pytest.raises(ValueError, match="réservé"):
        store.load_dataframe("Audit_Analysis_Runs", pd.DataFrame({"a": [1]}))


def test_history_tables_are_hidden_from_a_reloaded_store(tmp_path, monkeypatch):
    monkeypatch.setenv("SOVEREIGN_DB_PATH", str(tmp_path / "s.duckdb"))
    s1 = DataStore()
    s1.load_dataframe("ventes", pd.DataFrame({"a": [1]}))
    from app.financial import runs
    runs.ensure_tables(s1)
    s1.con.close()
    s2 = DataStore()                                           # redémarrage : relecture depuis le fichier
    assert "ventes" in s2.tables and not {"audit_analysis_runs", "audit_calculation_results"} & s2.tables
    assert "audit_" not in s2.schema_description()             # ni dans le prompt de l'IA


# ── intégrité à la lecture ─────────────────────────────────────────────────

def test_integrity_is_recomputed_and_detects_tampering(env):
    c, store, _ = env
    run = post(c).json()
    assert run["integrity"] == "ok"
    store.con.execute("UPDATE audit_calculation_results SET value = '1.00' WHERE run_id = ?", [run["run_id"]])
    assert c.get(f"/financial/runs/{run['run_id']}", headers=VIEWER).json()["integrity"] == "mismatch"
    run2 = post(c).json()
    store.con.execute("UPDATE audit_analysis_runs SET inputs_json = replace(inputs_json, '114000000', '1') WHERE run_id = ?", [run2["run_id"]])
    assert c.get(f"/financial/runs/{run2['run_id']}", headers=VIEWER).json()["integrity"] == "mismatch"


# ── M1 / M3 : entrées extrêmes ─────────────────────────────────────────────

@pytest.mark.parametrize("value", ["1E-999990", "1E+400", "1e31", "0." + "0" * 40 + "1", "1" * 60])
def test_extreme_magnitudes_are_refused_before_computation(env, value):
    c, *_ = env
    r = post(c, {"formula_code": "BUD001", "inputs": {"budget_vote": value, "depenses": "1"}})
    assert r.status_code == 422 and r.json()["detail"]["code"] == "invalid_value", r.text
    assert c.get("/financial/runs", headers=VIEWER).json()["runs"] == []


def test_huge_json_integer_and_unconvertible_float_sums_give_422_not_500(env):
    c, store, _ = env
    r = c.post("/financial/runs", content='{"formula_code":"BUD001","inputs":{"budget_vote":' + "9" * 5000 + ',"depenses":1}}',
               headers={**EDITOR, "content-type": "application/json"})
    assert r.status_code in (400, 422)                  # refus contrôlé (analyse du corps ou validation), jamais 500
    store.load_dataframe("gros", pd.DataFrame({"m": [1e40, 2.0]}))
    r = post(c, {"formula_code": "BUD001", "inputs": {"depenses": "1"},
                 "from_table": {"budget_vote": {"table": "gros", "column": "m"}}})
    assert r.status_code == 422 and r.json()["detail"]["code"] == "aggregation_failed"


# ── M2 : journal d'audit indisponible → échec fermé ────────────────────────

def test_run_is_refused_and_not_stored_when_the_audit_log_is_unwritable(env, monkeypatch):
    c, store, tmp = env
    ok = post(c).json()
    (tmp / "blocker").write_text("x")                                  # un fichier là où il faudrait un dossier
    monkeypatch.setattr(feedback, "AUDIT_PATH", tmp / "blocker" / "audit.jsonl")
    r = post(c)
    assert r.status_code == 503 and "Journal d'audit" in r.text
    count = store.con.execute("SELECT count(*) FROM audit_analysis_runs").fetchone()[0]
    assert count == 1 and ok["run_id"]


def test_access_denied_is_audited(env, monkeypatch):
    c, store, tmp = env
    load(store)
    (tmp / "pol.yaml").write_text(yaml.safe_dump({"policies": [{"table": "budget_2026", "column": "ligne", "scope": "ligne"}]}))
    monkeypatch.setenv("SOVEREIGN_ROW_POLICIES", str(tmp / "pol.yaml"))
    assert post(c, TABLE_RUN, EDITOR).status_code == 403
    lines = [json.loads(x)["action"] for x in (tmp / "audit.jsonl").read_text().splitlines()]
    assert "financial_run_denied" in lines

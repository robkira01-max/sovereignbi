"""P-080 / MOYEN-1 : sources de confiance du « Calculé », périmètre demandé, protection et empreinte des tables."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from app.data.duckdb_store import DataStore, ProtectedTableError, ReservedTableError
from app.financial import trusted
from app.pipeline.formula_route import route_formula
from app.semantic.model import load_model
from app.semantic.validate import validate_model

ROOT = Path(__file__).resolve().parents[1]


def bud(model):
    return next(m for m in model.metrics if m.formula == "BUD001")


@pytest.fixture()
def env():
    from app.financial.registry import get_registry
    get_registry()
    store = DataStore()
    from app.audit_data.reference import load_reference_tables
    load_reference_tables(store, ROOT / "data" / "audit_reference")
    model = load_model(str(ROOT / "semantic" / "model.yaml"))
    trusted.set_model_provider(lambda: model)
    yield store, model
    trusted.set_model_provider(None)


def ask(env, q, role="editor"):
    store, model = env
    return route_formula(model, q, store, actor="t", role=role)


# ── les trois cas de référence, par entité et exercice ──────────────────────

@pytest.mark.parametrize("q,value", [
    ("taux d'exécution budgétaire de Entité Alpha pour 2026", "95"),
    ("taux d'exécution budgétaire de Entité Bravo pour 2026", "114"),
])
def test_reference_cases_budget(env, q, value):
    r = ask(env, q)
    assert r["provenance"] == "calculated" and float(r["value"]) == float(value), r["answer"]


def test_reference_case_recovery_and_overrun(env):
    r = ask(env, "taux de recouvrement de Entité Charlie pour 2026")
    assert r["provenance"] == "calculated" and float(r["value"]) == 90
    r = ask(env, "dépassement budgétaire de Entité Bravo pour 2026")
    assert float(r["value"]) == 7000000


def test_other_fiscal_year_is_not_mixed_in(env):
    r = ask(env, "taux d'exécution budgétaire de Entité Alpha pour 2025")
    assert float(r["value"]) == 80          # 80 / 100, jamais mélangé à 2026


# ── période ou entité manquante : on pose la question, on ne devine pas ────

def test_missing_entity_or_year_asks_instead_of_guessing(env):
    r = ask(env, "taux d'exécution budgétaire pour 2026")
    assert r["provenance"] == "formula_unavailable" and r.get("value") is None
    assert "entité" in r["answer"] and "Entité Alpha" in r["answer"] and r["missing_scope"] == ["entite"]
    r = ask(env, "taux d'exécution budgétaire de Entité Alpha")
    assert r["missing_scope"] == ["exercice"] and r.get("value") is None
    r = ask(env, "taux d'exécution budgétaire")
    assert set(r["missing_scope"]) == {"entite", "exercice"}


def test_two_entities_in_the_question_is_ambiguous(env):
    r = ask(env, "taux d'exécution budgétaire de Entité Alpha et Entité Bravo pour 2026")
    assert r["provenance"] == "formula_unavailable" and "entite" in r["missing_scope"]


# ── empreinte du contenu dans le run ────────────────────────────────────────

def test_run_records_content_fingerprint_that_follows_the_data(env):
    store, _ = env
    q = "taux d'exécution budgétaire de Entité Alpha pour 2026"
    from app.financial import runs
    run1 = runs.get_run(store, ask(env, q)["run_id"], actor="t", is_admin=True)
    src1 = run1["sources"]["budget_vote"]
    assert len(src1["table_fingerprint"]) == 64 and src1["table_rows"] == 5 and src1["where"]["entite"] == "Entité Alpha"
    store.con.execute("UPDATE audit_ref_budget SET depenses = depenses + 1 WHERE entite = 'Entité Charlie'")   # contenu modifié ailleurs dans la table
    run2 = runs.get_run(store, ask(env, q)["run_id"], actor="t", is_admin=True)
    assert run2["sources"]["budget_vote"]["table_fingerprint"] != src1["table_fingerprint"]
    assert run2["result_hash"] != run1["result_hash"]          # même valeur 95, mais autre état de la table : autre empreinte de run


# ── source de confiance ─────────────────────────────────────────────────────

def test_user_table_never_serves_a_calculated_number(env):
    store, model = env
    store.load_dataframe("ma_table", pd.DataFrame({"entite": ["X"], "exercice": [2026], "devise": ["DJF"],
                                                   "budget_vote": [10], "depenses": [9]}))
    for m in model.metrics:
        if m.formula:
            for b in m.formula_inputs.values():
                b["table"] = "ma_table"
    r = ask(env, "taux d'exécution budgétaire de X pour 2026")
    assert r["provenance"] == "formula_unavailable" and r.get("value") is None and "pack Audit" in r["answer"]


def test_validate_rejects_formula_source_that_is_an_uploaded_table(env):
    store, model = env
    assert [i for i in validate_model(model) if i.level == "error"] == []
    bud(model).formula_inputs["depenses"]["table"] = "clients"
    codes = {i.code for i in validate_model(model)}
    assert "untrusted_formula_source" in codes


def test_validate_rejects_unknown_aggregation_and_filter_column(env):
    _, model = env
    bud(model).formula_inputs["depenses"]["agg"] = "max"
    bud(model).formula_inputs["budget_vote"]["filters"] = {"nope": "x"}
    codes = [i.code for i in validate_model(model)]
    assert "unsupported_aggregation" in codes and codes.count("unknown_column") >= 1


# ── MOYEN-1 : un upload ne crée ni ne remplace une table du pack / une source de calcul ──

def test_upload_cannot_create_or_replace_audit_namespace(env):
    store, _ = env
    df = pd.DataFrame({"a": [1]})
    with pytest.raises(ReservedTableError):
        store.load_dataframe("audit_ref_budget", df)         # remplacement de la table de référence
    with pytest.raises(ReservedTableError):
        store.load_dataframe("audit_nouvelle", df)            # création dans l'espace réservé
    assert store.con.execute("SELECT count(*) FROM audit_ref_budget").fetchone()[0] == 5


def test_table_referenced_by_formula_inputs_cannot_be_replaced_by_any_role(env):
    store, model = env
    store.load_dataframe("ventes_ext", pd.DataFrame({"v": [1]}))
    bud(model).formula_inputs["depenses"] = {"table": "ventes_ext", "column": "v", "agg": "sum", "filters": {}}
    with pytest.raises(ProtectedTableError):
        store.load_dataframe("ventes_ext", pd.DataFrame({"v": [999]}))
    assert store.con.execute("SELECT v FROM ventes_ext").fetchone()[0] == 1       # inchangée
    trusted.set_model_provider(None)
    store.load_dataframe("ventes_ext", pd.DataFrame({"v": [2]}))                   # non référencée : remplaçable


def test_upload_route_returns_409_with_explicit_message(env, monkeypatch):
    from fastapi.testclient import TestClient
    import app.main as m
    store, model = env
    store.load_dataframe("ventes_ext", pd.DataFrame({"v": [1]}))
    bud(model).formula_inputs["depenses"] = {"table": "ventes_ext", "column": "v", "agg": "sum", "filters": {}}
    monkeypatch.setattr(m, "store", store)
    monkeypatch.setattr(trusted, "_provider", lambda: model)
    with TestClient(m.app) as c:
        trusted.set_model_provider(lambda: model)
        monkeypatch.setattr(m, "store", store)
        for key in ("test-viewer-key-s6", "test-admin-key-sprint3"):
            r = c.post("/upload", files={"file": ("ventes_ext.csv", b"v\n5\n", "text/csv")}, headers={"X-Api-Key": key})
            assert r.status_code == 409 and "ne peut pas être remplacée" in r.json()["detail"], (key, r.text)
        r = c.post("/upload", files={"file": ("audit_ref_budget.csv", b"a\n1\n", "text/csv")}, headers={"X-Api-Key": "test-admin-key-sprint3"})
        assert r.status_code == 400


# ── revue sécurité : contournements fermés ──────────────────────────────────

def _sched(target):
    from app.sync.models import SyncSchedule
    return SyncSchedule(schedule_id="s", connector_type="postgres", name="n", host="h", port=1, database="d", username="u",
                        password_enc="x", query_or_table="t", target_table=target, cron_expr="* * * * *")


@pytest.mark.parametrize("target", ["audit_ref_budget", "audit_financial_records", "audit_findings", "audit_nouvelle"])
def test_scheduled_sync_cannot_write_audit_tables(env, target, monkeypatch):
    from app.sync import sync_engine
    store, _ = env
    monkeypatch.setattr(sync_engine, "save_schedule", lambda s: None, raising=False)
    monkeypatch.setattr(sync_engine, "save_run", lambda r: None, raising=False)
    before = store.con.execute("SELECT count(*) FROM audit_ref_budget").fetchone()[0]
    run = sync_engine.run_sync(_sched(target), store, connector_factory=lambda s, p: pd.DataFrame({"a": [1]}))
    assert getattr(run, "status", "") != "success"
    assert store.con.execute("SELECT count(*) FROM audit_ref_budget").fetchone()[0] == before


def test_scheduled_sync_cannot_replace_a_formula_source(env, monkeypatch):
    from app.sync import sync_engine
    store, model = env
    store.load_dataframe("src_ext", pd.DataFrame({"v": [1]}))
    bud(model).formula_inputs["depenses"] = {"table": "src_ext", "column": "v", "agg": "sum", "filters": {}}
    monkeypatch.setattr(sync_engine, "save_schedule", lambda s: None, raising=False)
    monkeypatch.setattr(sync_engine, "save_run", lambda r: None, raising=False)
    sync_engine.run_sync(_sched("src_ext"), store, connector_factory=lambda s, p: pd.DataFrame({"v": [999]}))
    assert store.con.execute("SELECT v FROM src_ext").fetchone()[0] == 1


def test_sync_schedule_creation_refuses_reserved_target():
    from app.routers.sync import SyncScheduleCreate
    with pytest.raises(ValueError):
        SyncScheduleCreate(connector_type="postgres", name="n", host="h", port=1, database="d", username="u", password="p",
                           query_or_table="t", target_table="audit_financial_records", cron_expr="* * * * *")


def test_audit_financial_records_and_persisted_audit_tables_are_not_trusted(env):
    store, model = env
    store.con.execute("CREATE TABLE audit_financial_records (montant DECIMAL(38,6))")      # alimentée par des imports utilisateurs
    store.con.execute("CREATE TABLE audit_heritee (v BIGINT)")                              # retrouvée dans un fichier persistant
    store.tables |= {"audit_financial_records", "audit_heritee"}
    assert trusted.untrusted_reason(store, "audit_financial_records") is not None
    assert trusted.untrusted_reason(store, "audit_heritee") is not None
    assert trusted.untrusted_reason(store, "audit_ref_budget") is None
    assert not trusted.is_audit_namespace("audit_financial_records")


def test_replace_guard_fails_closed_when_model_is_unreadable(env):
    store, _ = env
    store.load_dataframe("quelconque", pd.DataFrame({"v": [1]}))
    def boom():
        raise RuntimeError("yaml cassé")
    trusted.set_model_provider(boom)
    with pytest.raises(ProtectedTableError):
        store.load_dataframe("quelconque", pd.DataFrame({"v": [2]}))
    assert store.con.execute("SELECT v FROM quelconque").fetchone()[0] == 1


def test_guard_covers_every_sector_model_not_only_the_active_one(env):
    store, model = env
    store.load_dataframe("src_secteur", pd.DataFrame({"v": [1]}))
    other = load_model(str(ROOT / "semantic" / "model.yaml"))
    bud(other).formula_inputs["depenses"] = {"table": "src_secteur", "column": "v", "agg": "sum", "filters": {}}
    trusted.set_model_provider(lambda: [model, other])
    with pytest.raises(ProtectedTableError):
        store.load_dataframe("src_secteur", pd.DataFrame({"v": [2]}))


def test_fixed_filter_wins_over_scope_and_overlap_is_a_config_error(env):
    _, model = env
    bud(model).formula_scope.append({"column": "devise", "label": "devise"})
    assert "scope_filter_overlap" in {i.code for i in validate_model(model)}


def test_malformed_filter_value_is_a_controlled_refusal_not_a_500(env):
    _, model = env
    bud(model).formula_inputs["depenses"]["filters"] = {"devise": 1.5}
    r = ask(env, "taux d'exécution budgétaire de Entité Alpha pour 2026")
    assert r["provenance"] == "formula_unavailable" and r.get("value") is None

"""Persistance des analyses (P-073) : tables DuckDB `audit_analysis_runs` et `audit_calculation_results`.

- Écriture : requêtes paramétrées sur la connexion du store (DDL + INSERT, aucune ligne de client lue).
- Lecture : toujours par `DataStore.execute` (sécurité par ligne P-068, décision D-3 du pack Audit). Le SQL ne
  reçoit que des valeurs validées (UUID, entiers bornés, identifiant d'auteur filtré), jamais du texte libre.
- Un run n'est jamais modifié ni supprimé par ce module. Ces tables sont réservées (`RESERVED_TABLES` dans
  duckdb_store) : ni importables par un utilisateur, ni visibles de l'IA.
- Visibilité : un run dont une entrée vient d'une table (`uses_table`) contient un agrégat calculé avec les droits
  de son auteur ; seul cet auteur et un admin peuvent le relire (sinon la sécurité par ligne serait contournée).
- Intégrité : `integrity` recalcule les hash à la lecture. Ce n'est PAS une signature : quelqu'un qui peut écrire
  directement dans la base peut forger un run cohérent. Il détecte une altération partielle ou accidentelle.
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from app.financial.engine import CalcResult, canonical, input_snapshot_hash, result_hash

RUNS = "audit_analysis_runs"
RESULTS = "audit_calculation_results"
_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_ACTOR_RE = re.compile(r"^[A-Za-z0-9:_.@-]{1,80}$")
_RUN_COLS = ("run_id", "created_at", "created_by", "engine_version", "ruleset_version", "formula_code",
             "formula_version", "definition_hash", "input_snapshot_hash", "result_hash", "status", "inputs_json",
             "uses_table")
_RES_COLS = ("run_id", "formula_code", "formula_version", "value", "raw_value", "unit", "status", "message")


def valid_run_id(run_id: str) -> bool:
    return bool(_UUID_RE.match(run_id or ""))


def new_run_id() -> str:
    return str(uuid.uuid4())


def ensure_tables(store) -> None:
    store.con.execute(f"""CREATE TABLE IF NOT EXISTS {RUNS} (
        run_id VARCHAR PRIMARY KEY, created_at VARCHAR, created_by VARCHAR, engine_version VARCHAR,
        ruleset_version VARCHAR, formula_code VARCHAR, formula_version INTEGER, definition_hash VARCHAR,
        input_snapshot_hash VARCHAR, result_hash VARCHAR, status VARCHAR, inputs_json VARCHAR, uses_table BOOLEAN)""")
    store.con.execute(f"""CREATE TABLE IF NOT EXISTS {RESULTS} (
        run_id VARCHAR, formula_code VARCHAR, formula_version INTEGER, value VARCHAR, raw_value VARCHAR,
        unit VARCHAR, status VARCHAR, message VARCHAR)""")


def save_run(store, *, run_id: str, created_by: str, engine_version: str, ruleset_version: str, res: CalcResult,
             snapshot_hash: str, res_hash: str, sources: dict) -> str:
    if not valid_run_id(run_id):
        raise ValueError("run_id invalide")
    ensure_tables(store)
    uses_table = any("table" in s for s in sources.values())
    inputs_json = json.dumps({"inputs": {k: canonical(v) for k, v in sorted(res.inputs.items())},
                              "sources": sources}, sort_keys=True, ensure_ascii=False)
    store.con.execute(f"INSERT INTO {RUNS} VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", [
        run_id, datetime.now(tz=timezone.utc).isoformat(), created_by, engine_version, ruleset_version,
        res.formula_code, res.formula_version, res.definition_hash, snapshot_hash, res_hash, res.status,
        inputs_json, uses_table])
    store.con.execute(f"INSERT INTO {RESULTS} VALUES (?,?,?,?,?,?,?,?)", [
        run_id, res.formula_code, res.formula_version,
        None if res.value is None else format(res.value, "f"),   # précision de la formule conservée (95.00)
        None if res.raw_value is None else canonical(res.raw_value), res.unit, res.status, res.message])
    return run_id


def _rows(store, sql: str) -> list[dict]:
    cols, rows = store.execute(sql)
    return [dict(zip(cols, r, strict=True)) for r in rows]


def _visibility_clause(actor: str, is_admin: bool) -> str:
    if is_admin:
        return "TRUE"
    if not _ACTOR_RE.match(actor or ""):
        return "uses_table = FALSE"           # auteur non reconnaissable : seulement les runs sans table
    return f"(uses_table = FALSE OR created_by = '{actor}')"


def _integrity(run: dict) -> str:
    """Recalcule snapshot et result hash depuis ce qui est stocké ; « ok » ou « mismatch »."""
    try:
        res = run["result"]
        inputs = {k: Decimal(v) for k, v in run["inputs"].items()}
        snap = input_snapshot_hash(inputs, run["sources"])
        probe = CalcResult(
            formula_code=run["formula_code"], formula_version=run["formula_version"],
            definition_hash=run["definition_hash"], status=res["status"],
            value=None if res["value"] is None else Decimal(res["value"]),
            raw_value=None if res["raw_value"] is None else Decimal(res["raw_value"]),
            unit=res["unit"], message=res["message"] or "", inputs=inputs)
        return "ok" if snap == run["input_snapshot_hash"] and result_hash(probe, snap) == run["result_hash"] else "mismatch"
    except (KeyError, TypeError, ArithmeticError, ValueError):
        return "mismatch"


def get_run(store, run_id: str, *, actor: str, is_admin: bool) -> dict | None:
    """None si le run n'existe pas OU n'est pas visible pour cet appelant (même réponse : pas d'oracle)."""
    if not valid_run_id(run_id):
        return None
    ensure_tables(store)
    runs = _rows(store, f"SELECT {', '.join(_RUN_COLS)} FROM {RUNS} WHERE run_id = '{run_id}' "
                        f"AND {_visibility_clause(actor, is_admin)}")
    if not runs:
        return None
    run = runs[0]
    res = _rows(store, f"SELECT {', '.join(_RES_COLS[1:])} FROM {RESULTS} WHERE run_id = '{run_id}'")
    parsed = json.loads(run.pop("inputs_json"))
    run["inputs"], run["sources"] = parsed["inputs"], parsed["sources"]
    run["result"] = res[0] if res else None
    run["integrity"] = _integrity(run)
    return run


def list_runs(store, *, actor: str, is_admin: bool, formula_code: str | None = None,
              limit: int = 50, offset: int = 0) -> list[dict]:
    ensure_tables(store)
    limit, offset = max(1, min(int(limit), 200)), max(0, int(offset))
    clauses = [_visibility_clause(actor, is_admin)]
    if formula_code:
        if not re.match(r"^[A-Z][A-Z0-9_]{1,31}$", formula_code):
            return []
        clauses.append(f"formula_code = '{formula_code}'")
    cols = [c for c in _RUN_COLS if c != "inputs_json"]
    return _rows(store, f"SELECT {', '.join(cols)} FROM {RUNS} WHERE {' AND '.join(clauses)} "
                        f"ORDER BY created_at DESC LIMIT {limit} OFFSET {offset}")

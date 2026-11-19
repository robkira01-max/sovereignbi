"""Formules financières versionnées et analyses reproductibles (P-073).

Rôles : consultation = viewer ; lancer un calcul = editor. Toute lecture de données passe par
`DataStore.execute` (sécurité par ligne). Les montants sont échangés en CHAÎNES (jamais en flottants JSON).
"""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation, localcontext
from typing import Literal

import duckdb
import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.feedback import record_audit
from app.financial import runs
from app.financial.engine import ENGINE_VERSION, CalculationError, calculate, canonical, input_snapshot_hash, result_hash
from app.financial.registry import RegistryError, get_registry
from app.security import row_policy
from app.security.rbac import RequireRole

router = APIRouter(prefix="/financial", tags=["financial"])
_VIEWER, _EDITOR = RequireRole("viewer"), RequireRole("editor")
log = structlog.get_logger()

_IDENT = r"^[A-Za-z_][A-Za-z0-9_]{0,63}$"
_NATIVE = re.compile(r"^(TINYINT|SMALLINT|INTEGER|BIGINT|HUGEINT|UTINYINT|USMALLINT|UINTEGER|UBIGINT|UHUGEINT|DECIMAL\(\d+,\s*\d+\))$")
_FLOAT = {"DOUBLE", "FLOAT", "REAL"}
CAST = "DECIMAL(38,6)"


def _audit(action: str, **details) -> None:
    try:
        record_audit(action, details)
    except OSError:
        log.error("audit_write_failed", action=action)


def _audit_strict(action: str, **details) -> None:
    """Action sensible : si le journal d'audit est inscriptible nulle part, on refuse (échec fermé), rien n'est stocké."""
    try:
        record_audit(action, details)
    except OSError:
        log.error("audit_write_failed", action=action)
        raise HTTPException(503, "Journal d'audit indisponible : calcul non enregistré.") from None


def _actor(request: Request, role: str) -> str:
    if request.headers.get("x-api-key"):
        return f"api_key:{role}"      # une clé n'est pas une personne : on distingue au moins le rôle
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        from app.auth.security import verify_session
        u = verify_session(auth[7:])
        if u:
            return f"user:{u['id']}"
    return "unknown"


class TableBinding(BaseModel):
    table: str = Field(pattern=_IDENT)
    column: str = Field(pattern=_IDENT)
    agg: Literal["sum"] = "sum"


class RunBody(BaseModel):
    formula_code: str = Field(pattern=r"^[A-Z][A-Z0-9_]{1,31}$")
    version: int | None = Field(None, ge=1, le=10_000, description="Dernière version si absent")
    inputs: dict[str, str | int] = Field(default_factory=dict, max_length=32,
                                         description="Valeurs explicites (chaînes décimales de préférence)")
    from_table: dict[str, TableBinding] = Field(default_factory=dict, max_length=32,
                                                description="Variable → somme d'une colonne de table (lecture sécurisée par ligne)")


def _to_decimal(name: str, value: str | int) -> Decimal:
    try:
        d = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):     # ValueError : entier JSON démesuré (limite de conversion Python)
        raise CalculationError("invalid_value", f"« {name} » n'est pas un nombre décimal.") from None
    if not d.is_finite() or len(str(value)) > 60:
        raise CalculationError("invalid_value", f"« {name} » doit être un nombre fini.")
    return d


def _bind(store, name: str, b: TableBinding) -> tuple[Decimal | None, dict]:
    tables = {t.lower(): t for t in store.tables}
    real = tables.get(b.table.lower())
    if real is None:
        raise CalculationError("unknown_table", f"Table inconnue pour « {name} » : {b.table}.")
    cols = store.con.execute(    # métadonnées de schéma seulement, aucune ligne
        "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = ?", [real]).fetchall()
    col = next(((c, t) for c, t in cols if c.lower() == b.column.lower()), None)
    if col is None:
        raise CalculationError("unknown_column", f"Colonne inconnue pour « {name} » : {b.table}.{b.column}.")
    cname, ctype = col[0], str(col[1]).upper()
    qtab, qcol = real.replace('"', '""'), cname.replace('"', '""')     # défense en profondeur (identifiants déjà filtrés)
    source = {"table": real, "column": cname, "agg": b.agg}
    if _NATIVE.match(ctype):
        expr = f'"{qcol}"'
    elif ctype in _FLOAT:
        expr = f'CAST("{qcol}" AS {CAST})'
        source["cast"] = CAST      # conversion exacte déclarée : visible dans le run
    else:
        raise CalculationError("unsupported_column", f"{real}.{cname} est de type {ctype} : seule une colonne numérique est acceptée.")
    try:
        _, rows = store.execute(f'SELECT sum({expr}) FROM "{qtab}"')
    except duckdb.Error:      # dépassement de capacité, NaN/inf non convertible… : refus maîtrisé, pas de 500
        raise CalculationError("aggregation_failed", f"Agrégation impossible sur {real}.{cname} (valeurs hors limites ?).") from None
    total = rows[0][0] if rows else None
    return (None if total is None else Decimal(str(total))), source


@router.get("/formulas")
def list_formulas(all_versions: bool = Query(False), family: str | None = Query(None, max_length=32),
                  _: str = Depends(_VIEWER)):
    reg = get_registry()
    out = []
    for code in reg.codes():
        f = reg.formulas[code]
        versions = list(f.versions.values()) if all_versions else [f.latest]
        out += [v.public() for v in versions if family is None or v.family == family]
    return {"engine_version": ENGINE_VERSION, "formulas": out}


@router.get("/formulas/{code}")
def get_formula(code: str, version: int | None = Query(None, ge=1), _: str = Depends(_VIEWER)):
    reg = get_registry()
    try:
        if version is None:
            f = reg.formulas.get(code)
            if f is None:
                raise RegistryError(f"Formule inconnue : « {code} ».")
            return {"code": code, "versions": [v.public() for v in f.versions.values()]}
        return reg.get(code, version).public()
    except RegistryError as e:
        raise HTTPException(404, str(e)) from None


@router.post("/runs", status_code=201)
def run_calculation(body: RunBody, request: Request, role: str = Depends(_EDITOR)):
    reg, store, actor = get_registry(), request.app.state.store, _actor(request, role)
    try:
        fv = reg.get(body.formula_code, body.version)
    except RegistryError as e:
        raise HTTPException(404, str(e)) from None
    try:
        clash = set(body.inputs) & set(body.from_table)
        if clash:
            raise CalculationError("duplicate_source", f"Variable(s) fournie(s) deux fois : {', '.join(sorted(clash))}.")
        given: dict[str, Decimal | None] = {k: _to_decimal(k, v) for k, v in body.inputs.items()}
        sources: dict[str, dict] = {k: {"explicit": True} for k in body.inputs}
        for name, binding in body.from_table.items():
            given[name], sources[name] = _bind(store, name, binding)
        res = calculate(fv, given)   # type: ignore[arg-type]
    except row_policy.AccessDenied as e:
        _audit("financial_run_denied", formula=fv.code, version=fv.version, actor=actor)
        raise HTTPException(403, str(e)) from None
    except CalculationError as e:
        _audit("financial_run_rejected", formula=fv.code, version=fv.version, reason=e.code, actor=actor)
        raise HTTPException(422, {"code": e.code, "message": str(e)}) from None

    snap = input_snapshot_hash(res.inputs, sources)
    rh = result_hash(res, snap)
    run_id = runs.new_run_id()
    _audit_strict("financial_run", run_id=run_id, formula=fv.code, version=fv.version, result_hash=rh, actor=actor)
    runs.save_run(store, run_id=run_id, created_by=actor, engine_version=ENGINE_VERSION,
                  ruleset_version=reg.ruleset_version([fv]), res=res, snapshot_hash=snap, res_hash=rh, sources=sources)
    return _with_definition_status(runs.get_run(store, run_id, actor=actor, is_admin=role == "admin"))


def _with_definition_status(run: dict) -> dict:
    """Signale si la définition de la formule a changé depuis le run (modification « en place » d'une version)."""
    try:
        current = get_registry().get(run["formula_code"], run["formula_version"]).definition_hash
        run["definition_status"] = "unchanged" if current == run["definition_hash"] else "definition_changed"
    except RegistryError:
        run["definition_status"] = "formula_missing"
    return run


@router.get("/runs")
def list_runs(request: Request, formula_code: str | None = Query(None, max_length=32),
              limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), role: str = Depends(_VIEWER)):
    try:
        return {"runs": runs.list_runs(request.app.state.store, actor=_actor(request, role), is_admin=role == "admin",
                                       formula_code=formula_code, limit=limit, offset=offset)}
    except row_policy.AccessDenied as e:
        raise HTTPException(403, str(e)) from None


def _load(store, run_id: str, actor: str, role: str) -> dict:
    try:
        run = runs.get_run(store, run_id, actor=actor, is_admin=role == "admin")
    except row_policy.AccessDenied as e:
        raise HTTPException(403, str(e)) from None
    if run is None:
        raise HTTPException(404, "Analyse introuvable.")
    return _with_definition_status(run)


@router.get("/runs/{run_id}")
def get_run(run_id: str, request: Request, role: str = Depends(_VIEWER)):
    return _load(request.app.state.store, run_id, _actor(request, role), role)


@router.get("/runs/{run_a}/compare/{run_b}")
def compare_runs(run_a: str, run_b: str, request: Request, role: str = Depends(_VIEWER)):
    store, actor = request.app.state.store, _actor(request, role)
    a, b = _load(store, run_a, actor, role), _load(store, run_b, actor, role)
    names = sorted(set(a["inputs"]) | set(b["inputs"]))
    diffs = {n: {"a": a["inputs"].get(n), "b": b["inputs"].get(n)} for n in names if a["inputs"].get(n) != b["inputs"].get(n)}
    same_formula = (a["formula_code"], a["formula_version"]) == (b["formula_code"], b["formula_version"])
    va, vb = (a["result"] or {}).get("value"), (b["result"] or {}).get("value")
    delta = None
    if same_formula and va is not None and vb is not None:
        with localcontext() as ctx:
            ctx.prec = 50
            delta = canonical(Decimal(vb) - Decimal(va))
    return {"a": run_a, "b": run_b, "same_formula_and_version": same_formula,
            "same_result_hash": a["result_hash"] == b["result_hash"], "same_inputs": not diffs,
            "input_differences": diffs, "value_a": va, "value_b": vb, "delta_b_minus_a": delta,
            "definition_status": {"a": a["definition_status"], "b": b["definition_status"]}}

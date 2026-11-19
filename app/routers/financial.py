"""Formules financières versionnées et analyses reproductibles (P-073).

Rôles : consultation = viewer ; lancer un calcul = editor. Toute lecture de données passe par
`DataStore.execute` (sécurité par ligne). Les montants sont échangés en CHAÎNES (jamais en flottants JSON).
"""
from __future__ import annotations

from decimal import Decimal, localcontext

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.financial import runs
from app.financial.engine import ENGINE_VERSION, CalculationError, canonical
from app.financial.registry import RegistryError, get_registry
from app.financial.service import TableBinding, perform_run, with_definition_status as _with_definition_status
from app.security import row_policy
from app.security.actor import actor_label
from app.security.rbac import RequireRole

router = APIRouter(prefix="/financial", tags=["financial"])
_VIEWER, _EDITOR = RequireRole("viewer"), RequireRole("editor")

_IDENT = r"^[A-Za-z_][A-Za-z0-9_]{0,63}$"


class RunBody(BaseModel):
    formula_code: str = Field(pattern=r"^[A-Z][A-Z0-9_]{1,31}$")
    version: int | None = Field(None, ge=1, le=10_000, description="Dernière version si absent")
    inputs: dict[str, str | int] = Field(default_factory=dict, max_length=32,
                                         description="Valeurs explicites (chaînes décimales de préférence)")
    from_table: dict[str, TableBinding] = Field(default_factory=dict, max_length=32,
                                                description="Variable → somme d'une colonne de table (lecture sécurisée par ligne)")


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
    store, actor = request.app.state.store, actor_label(request, role)
    try:
        return perform_run(store, actor=actor, is_admin=role == "admin", formula_code=body.formula_code,
                           version=body.version, inputs=body.inputs, from_table=body.from_table)
    except RegistryError as e:
        raise HTTPException(404, str(e)) from None
    except row_policy.AccessDenied as e:
        raise HTTPException(403, str(e)) from None
    except CalculationError as e:
        raise HTTPException(422, {"code": e.code, "message": str(e)}) from None


@router.get("/runs")
def list_runs(request: Request, formula_code: str | None = Query(None, max_length=32),
              limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), role: str = Depends(_VIEWER)):
    try:
        return {"runs": runs.list_runs(request.app.state.store, actor=actor_label(request, role), is_admin=role == "admin",
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
    return _load(request.app.state.store, run_id, actor_label(request, role), role)


@router.get("/runs/{run_a}/compare/{run_b}")
def compare_runs(run_a: str, run_b: str, request: Request, role: str = Depends(_VIEWER)):
    store, actor = request.app.state.store, actor_label(request, role)
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

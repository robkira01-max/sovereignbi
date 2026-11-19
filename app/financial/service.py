"""Exécution d'un calcul financier, partagée par `/financial/runs` et le chat (P-080).

Un seul chemin de calcul : le chiffre du chat est donc celui de l'écran Formules pour le même run.
Toute lecture de données passe par `DataStore.execute` (sécurité par ligne, échec fermé).
Les erreurs (`CalculationError`, `row_policy.AccessDenied`) sont inscrites au journal puis relancées.
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from typing import Literal

import duckdb
from pydantic import BaseModel, Field

from app.financial import runs
from app.financial.engine import ENGINE_VERSION, CalculationError, calculate, input_snapshot_hash, result_hash
from app.financial.registry import RegistryError, get_registry
from app.security import row_policy
from app.security.actor import audit_soft, audit_strict

_IDENT = r"^[A-Za-z_][A-Za-z0-9_]{0,63}$"
_NATIVE = re.compile(r"^(TINYINT|SMALLINT|INTEGER|BIGINT|HUGEINT|UTINYINT|USMALLINT|UINTEGER|UBIGINT|UHUGEINT|DECIMAL\(\d+,\s*\d+\))$")
_FLOAT = {"DOUBLE", "FLOAT", "REAL"}
CAST = "DECIMAL(38,6)"


class TableBinding(BaseModel):
    table: str = Field(pattern=_IDENT)
    column: str = Field(pattern=_IDENT)
    agg: Literal["sum"] = "sum"


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


def perform_run(store, *, actor: str, is_admin: bool, formula_code: str, version: int | None,
                inputs: Mapping[str, str | int], from_table: Mapping[str, TableBinding], via: str = "api") -> dict:
    """Calcule, inscrit au journal, enregistre et renvoie le run. `RegistryError` si la formule est inconnue."""
    reg = get_registry()
    fv = reg.get(formula_code, version)
    try:
        clash = set(inputs) & set(from_table)
        if clash:
            raise CalculationError("duplicate_source", f"Variable(s) fournie(s) deux fois : {', '.join(sorted(clash))}.")
        given: dict[str, Decimal | None] = {k: _to_decimal(k, v) for k, v in inputs.items()}
        sources: dict[str, dict] = {k: {"explicit": True} for k in inputs}
        for name, binding in from_table.items():
            given[name], sources[name] = _bind(store, name, binding)
        res = calculate(fv, given)   # type: ignore[arg-type]
    except row_policy.AccessDenied:
        audit_soft("financial_run_denied", formula=fv.code, version=fv.version, actor=actor, via=via)
        raise
    except CalculationError as e:
        audit_soft("financial_run_rejected", formula=fv.code, version=fv.version, reason=e.code, actor=actor, via=via)
        raise

    snap = input_snapshot_hash(res.inputs, sources)
    rh = result_hash(res, snap)
    run_id = runs.new_run_id()
    audit_strict("financial_run", run_id=run_id, formula=fv.code, version=fv.version, result_hash=rh, actor=actor, via=via)
    runs.save_run(store, run_id=run_id, created_by=actor, engine_version=ENGINE_VERSION,
                  ruleset_version=reg.ruleset_version([fv]), res=res, snapshot_hash=snap, res_hash=rh, sources=sources)
    return with_definition_status(runs.get_run(store, run_id, actor=actor, is_admin=is_admin))


def with_definition_status(run: dict) -> dict:
    """Signale si la définition de la formule a changé depuis le run (modification « en place » d'une version)."""
    try:
        current = get_registry().get(run["formula_code"], run["formula_version"]).definition_hash
        run["definition_status"] = "unchanged" if current == run["definition_hash"] else "definition_changed"
    except RegistryError:
        run["definition_status"] = "formula_missing"
    return run

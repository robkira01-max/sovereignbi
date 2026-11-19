"""Moteur de calcul financier (P-073) : pur, déterministe, en Decimal. Aucun accès aux données ici.

Garanties :
- contexte Decimal fixe (précision 50, arrondi HALF_EVEN pour les opérations intermédiaires) : même entrée,
  même résultat, sur toute machine ;
- arrondi final explicite, propre à la formule (precision + rounding) ; on conserve aussi la valeur non arrondie ;
- valeurs manquantes, négatifs et division par zéro suivent la règle de la formule : erreur explicite ou
  résultat « indéfini » déclaré. Jamais de 0 ou de NaN silencieux.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Context, Decimal, DivisionByZero, InvalidOperation, Overflow, localcontext

from app.financial.registry import ROUNDING, FormulaVersion

ENGINE_VERSION = "1.0.0"
MAX_ABS_EXPONENT = 30     # |exposant| d'une entrée : refuse 1E-999990 (amplification de stockage) comme 1E+400
MAX_DIGITS = 38
_CTX = Context(prec=50, rounding=ROUND_HALF_EVEN, Emin=-999, Emax=999,
               traps=[DivisionByZero, InvalidOperation, Overflow])


class CalculationError(ValueError):
    """Entrée invalide ou calcul impossible selon la règle de la formule (message affichable)."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class CalcResult:
    formula_code: str
    formula_version: int
    definition_hash: str
    status: str                 # "ok" | "undefined"
    value: Decimal | None       # arrondi selon la formule
    raw_value: Decimal | None   # valeur non arrondie
    unit: str
    message: str
    inputs: dict[str, Decimal]  # entrées effectivement utilisées (défauts explicites inclus)


def canonical(d: Decimal) -> str:
    """Forme texte stable d'un Decimal (pas de notation scientifique, pas de zéros de queue)."""
    s = format(d.normalize(), "f")
    return "0" if s in ("-0", "") else s


def _resolve_inputs(fv: FormulaVersion, given: Mapping[str, Decimal]) -> dict[str, Decimal]:
    known = {v.name for v in fv.variables}
    extra = set(given) - known
    if extra:
        raise CalculationError("unknown_variable", f"Variable(s) inconnue(s) pour {fv.code} v{fv.version} : {', '.join(sorted(extra))}.")
    out: dict[str, Decimal] = {}
    for v in fv.variables:
        val = given.get(v.name)
        if val is None:
            if v.required:
                raise CalculationError("missing_value", f"Valeur manquante pour « {v.name} » ({v.label}).")
            val = v.default           # défaut explicite, déclaré dans la formule
        if not val.is_finite():
            raise CalculationError("invalid_value", f"« {v.name} » doit être un nombre fini.")
        if val != 0 and (abs(val.adjusted()) > MAX_ABS_EXPONENT or len(val.as_tuple().digits) > MAX_DIGITS):
            raise CalculationError("invalid_value", f"« {v.name} » est hors des limites supportées (ordre de grandeur ±1e{MAX_ABS_EXPONENT}, {MAX_DIGITS} chiffres).")
        if val < 0 and not v.allow_negative:
            raise CalculationError("negative_value", f"« {v.name} » ({v.label}) ne peut pas être négatif.")
        out[v.name] = val
    return out


def calculate(fv: FormulaVersion, given: Mapping[str, Decimal]) -> CalcResult:
    used = _resolve_inputs(fv, given)
    base = dict(formula_code=fv.code, formula_version=fv.version, definition_hash=fv.definition_hash,
                unit=fv.result_unit, inputs=used)
    with localcontext(_CTX):
        try:
            raw = fv.expr.evaluate(used)
        except (DivisionByZero, InvalidOperation):
            if fv.on_zero_division == "null":
                return CalcResult(status="undefined", value=None, raw_value=None,
                                  message="Résultat indéfini : division par zéro (règle de la formule).", **base)
            raise CalculationError("division_by_zero", f"Division par zéro dans {fv.code} v{fv.version} : calcul refusé.") from None
        except Overflow:
            raise CalculationError("overflow", "Valeur hors limites.") from None
        try:
            rounded = raw.quantize(Decimal(1).scaleb(-fv.precision), rounding=ROUNDING[fv.rounding])
        except InvalidOperation:
            raise CalculationError("overflow", "Valeur hors limites après arrondi.") from None
    return CalcResult(status="ok", value=rounded, raw_value=raw, message="", **base)


def input_snapshot_hash(inputs: Mapping[str, Decimal], sources: Mapping[str, object] | None = None) -> str:
    """Empreinte des entrées (valeurs canoniques + provenance déclarée)."""
    payload = {"inputs": {k: canonical(v) for k, v in sorted(inputs.items())}, "sources": sources or {}}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def result_hash(res: CalcResult, snapshot_hash: str) -> str:
    """Même formule + même version + mêmes entrées + même moteur ⇒ même hash (reproductibilité)."""
    payload = {"engine": ENGINE_VERSION, "formula": res.formula_code, "version": res.formula_version,
               "definition": res.definition_hash, "snapshot": snapshot_hash, "status": res.status,
               "value": None if res.value is None else canonical(res.value),
               "raw": None if res.raw_value is None else canonical(res.raw_value)}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

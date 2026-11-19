"""Registre de formules financières versionnées (P-073), lu depuis `rules/financial/*.yaml`.

Règles de versionnement :
- un fichier = une formule (`code`), avec une liste `versions` numérotées 1, 2, 3… sans trou ;
- changer le comportement d'un calcul = AJOUTER une version ; l'ancienne reste consultable ;
- `definition_hash` couvre ce qui change le résultat (expression, variables, unités, précision, arrondi,
  règle de division par zéro), pas les libellés ni les descriptions. Un run enregistre ce hash : si quelqu'un
  modifie une version existante « en place », la relecture du run le signale.

Une définition invalide fait échouer le chargement avec un message précis (jamais de formule ignorée en silence).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from decimal import ROUND_CEILING, ROUND_DOWN, ROUND_FLOOR, ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path

import yaml

from app.financial.expr import FUNCTIONS, Expr, ExpressionError

DEFAULT_DIR = Path(__file__).resolve().parents[2] / "rules" / "financial"
CODE_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,31}$")
VAR_RE = re.compile(r"^[a-z][a-z0-9_]{0,47}$")
ROUNDING = {"ROUND_HALF_UP": ROUND_HALF_UP, "ROUND_HALF_EVEN": ROUND_HALF_EVEN, "ROUND_DOWN": ROUND_DOWN,
            "ROUND_FLOOR": ROUND_FLOOR, "ROUND_CEILING": ROUND_CEILING}
ZERO_DIVISION = ("error", "null")
MAX_PRECISION = 10


class RegistryError(ValueError):
    pass


@dataclass(frozen=True)
class VariableSpec:
    name: str
    label: str
    unit: str
    required: bool = True
    allow_negative: bool = False
    default: Decimal | None = None


@dataclass(frozen=True)
class FormulaVersion:
    code: str
    family: str
    version: int
    label: str
    description: str
    expression: str
    result_unit: str
    precision: int
    rounding: str
    on_zero_division: str
    variables: tuple[VariableSpec, ...]
    interpretation: str
    definition_hash: str
    expr: Expr = field(repr=False, compare=False, default=None)  # type: ignore[assignment]

    def public(self) -> dict:
        return {
            "code": self.code, "family": self.family, "version": self.version, "label": self.label,
            "description": self.description, "expression": self.expression, "result_unit": self.result_unit,
            "precision": self.precision, "rounding": self.rounding, "on_zero_division": self.on_zero_division,
            "interpretation": self.interpretation, "definition_hash": self.definition_hash,
            "variables": [{"name": v.name, "label": v.label, "unit": v.unit, "required": v.required,
                           "allow_negative": v.allow_negative,
                           "default": None if v.default is None else str(v.default)} for v in self.variables],
        }


@dataclass(frozen=True)
class Formula:
    code: str
    versions: dict[int, FormulaVersion]

    @property
    def latest(self) -> FormulaVersion:
        return self.versions[max(self.versions)]


class FormulaRegistry:
    def __init__(self, formulas: dict[str, Formula]) -> None:
        self.formulas = formulas

    def codes(self) -> list[str]:
        return sorted(self.formulas)

    def get(self, code: str, version: int | None = None) -> FormulaVersion:
        f = self.formulas.get(code)
        if f is None:
            raise RegistryError(f"Formule inconnue : « {code} ».")
        if version is None:
            return f.latest
        if version not in f.versions:
            raise RegistryError(f"Version {version} inconnue pour {code} (disponibles : {sorted(f.versions)}).")
        return f.versions[version]

    def ruleset_version(self, used: list[FormulaVersion]) -> str:
        """Empreinte courte des définitions réellement utilisées par une analyse."""
        parts = sorted(f"{v.code}@{v.version}:{v.definition_hash}" for v in used)
        return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


# ── chargement ───────────────────────────────────────────────────────────────

def _fail(path: Path, msg: str) -> RegistryError:
    return RegistryError(f"{path.name} : {msg}")


def _decimal(path: Path, where: str, value) -> Decimal:
    try:
        d = Decimal(str(value))
    except InvalidOperation:
        raise _fail(path, f"{where} : « {value} » n'est pas un nombre.") from None
    if not d.is_finite():
        raise _fail(path, f"{where} : valeur non finie.")
    return d


def _definition_hash(code: str, version: int, raw: dict, variables: tuple[VariableSpec, ...]) -> str:
    canon = {
        "code": code, "version": version, "expression": raw["expression"].strip(),
        "result_unit": str(raw.get("result_unit", "")), "precision": raw["precision"],
        "rounding": raw["rounding"], "on_zero_division": raw["on_zero_division"],
        "variables": [{"name": v.name, "unit": v.unit, "required": v.required, "allow_negative": v.allow_negative,
                       "default": None if v.default is None else str(v.default)} for v in variables],
    }
    return hashlib.sha256(json.dumps(canon, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _parse_version(path: Path, code: str, family: str, raw: dict, expected: int) -> FormulaVersion:
    if not isinstance(raw, dict):
        raise _fail(path, f"version {expected} : entrée mal formée.")
    if raw.get("version") != expected or isinstance(raw.get("version"), bool):
        raise _fail(path, f"les versions doivent être numérotées 1, 2, 3… sans trou (attendu {expected}, lu {raw.get('version')!r}).")
    for key in ("label", "expression", "precision", "rounding", "on_zero_division", "variables"):
        if key not in raw:
            raise _fail(path, f"version {expected} : champ « {key} » manquant.")
    precision = raw["precision"]
    if not isinstance(precision, int) or isinstance(precision, bool) or not 0 <= precision <= MAX_PRECISION:
        raise _fail(path, f"version {expected} : precision doit être un entier entre 0 et {MAX_PRECISION}.")
    if raw["rounding"] not in ROUNDING:
        raise _fail(path, f"version {expected} : rounding inconnu (permis : {', '.join(ROUNDING)}).")
    if raw["on_zero_division"] not in ZERO_DIVISION:
        raise _fail(path, f"version {expected} : on_zero_division doit valoir {' ou '.join(ZERO_DIVISION)}.")
    if not isinstance(raw["variables"], dict) or not raw["variables"]:
        raise _fail(path, f"version {expected} : variables doit être une table non vide.")

    variables: list[VariableSpec] = []
    for name, spec in raw["variables"].items():
        if not isinstance(name, str) or not VAR_RE.match(name) or name in FUNCTIONS:
            raise _fail(path, f"version {expected} : nom de variable invalide « {name} ».")
        spec = spec or {}
        required = spec.get("required", True)
        if not isinstance(required, bool):
            raise _fail(path, f"version {expected} : {name}.required doit être vrai ou faux.")
        default = None
        if "default" in spec:
            if required:
                raise _fail(path, f"version {expected} : {name} a une valeur par défaut mais est obligatoire.")
            default = _decimal(path, f"version {expected} : {name}.default", spec["default"])
        elif not required:
            raise _fail(path, f"version {expected} : {name} est facultative : une valeur par défaut explicite est exigée.")
        variables.append(VariableSpec(name=name, label=str(spec.get("label", name)), unit=str(spec.get("unit", "")),
                                      required=required, allow_negative=bool(spec.get("allow_negative", False)),
                                      default=default))
    names = {v.name for v in variables}
    try:
        expr = Expr(raw["expression"], names)
    except ExpressionError as e:
        raise _fail(path, f"version {expected} : {e}") from None
    unused = names - expr.names
    if unused:
        raise _fail(path, f"version {expected} : variable(s) déclarée(s) mais non utilisée(s) : {', '.join(sorted(unused))}.")

    vt = tuple(variables)
    return FormulaVersion(
        code=code, family=family, version=expected, label=str(raw["label"]), description=str(raw.get("description", "")),
        expression=raw["expression"].strip(), result_unit=str(raw.get("result_unit", "")), precision=precision,
        rounding=raw["rounding"], on_zero_division=raw["on_zero_division"], variables=vt,
        interpretation=str(raw.get("interpretation", "")), definition_hash=_definition_hash(code, expected, raw, vt),
        expr=expr)


def _load_file(path: Path) -> Formula:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as e:
        raise _fail(path, f"illisible ({type(e).__name__}).") from None
    if not isinstance(data, dict):
        raise _fail(path, "le fichier doit contenir une table YAML.")
    code = data.get("code")
    if not isinstance(code, str) or not CODE_RE.match(code):
        raise _fail(path, "code invalide (A-Z, chiffres et _, 2 à 32 caractères).")
    if path.stem.upper() != code:
        raise _fail(path, f"le nom du fichier doit correspondre au code ({code.lower()}.yaml).")
    versions = data.get("versions")
    if not isinstance(versions, list) or not versions:
        raise _fail(path, "versions doit être une liste non vide.")
    family = str(data.get("family", ""))
    parsed = {i: _parse_version(path, code, family, raw, i) for i, raw in enumerate(versions, start=1)}
    return Formula(code=code, versions=parsed)


def load_registry(directory: Path | str | None = None) -> FormulaRegistry:
    d = Path(directory or os.environ.get("SOVEREIGN_FORMULAS_DIR") or DEFAULT_DIR)
    if not d.is_dir():
        raise RegistryError(f"Dossier de formules introuvable : {d}")
    formulas: dict[str, Formula] = {}
    for path in sorted(d.glob("*.yaml")):
        f = _load_file(path)
        if f.code in formulas:
            raise _fail(path, f"code {f.code} en double.")
        formulas[f.code] = f
    if not formulas:
        raise RegistryError(f"Aucune formule dans {d}")
    return FormulaRegistry(formulas)


_cache: tuple[tuple, FormulaRegistry] | None = None


def get_registry() -> FormulaRegistry:
    """Registre courant ; rechargé si un fichier YAML a changé (pas de redémarrage pour ajouter une version)."""
    global _cache
    d = Path(os.environ.get("SOVEREIGN_FORMULAS_DIR") or DEFAULT_DIR)
    key = (str(d), tuple((p.name, p.stat().st_mtime_ns) for p in sorted(d.glob("*.yaml")))) if d.is_dir() else (str(d), ())
    if _cache is None or _cache[0] != key:
        _cache = (key, load_registry(d))
    return _cache[1]

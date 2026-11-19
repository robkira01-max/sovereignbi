"""Chargement et validation des règles de contrôle d'audit (`rules/audit/*.yaml`) — P-075.

Une règle = un fichier : code, version, paramètres typés, SQL paramétré. Aucune IA. Le SQL n'est jamais fourni par
l'utilisateur : il vient de ce dépôt. Seules les VALEURS de paramètres viennent de l'appelant, validées puis formatées
par `render_params` (jamais interpolées brutes).
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

import yaml

DEFAULT_DIR = Path(__file__).resolve().parents[2] / "rules" / "audit"
_CODE = re.compile(r"AUD\d{3}")
_ACCOUNT = re.compile(r"[A-Za-z0-9._\- ]{1,40}")
_CCY = re.compile(r"[A-Z]{3}")
TYPES = {"int", "decimal", "date", "int_list", "budgets"}
MAX_BUDGETS = 500
DEFAULT_MAX = Decimal(10) ** 15
_KEYS = {"code", "version", "title", "severity", "indicative", "description", "interpretation", "requires",
         "applicable_if", "params", "message", "sql"}


class RuleError(ValueError):
    pass


class ParamError(ValueError):
    def __init__(self, param: str, message: str) -> None:
        super().__init__(f"{param} : {message}")
        self.param = param


@dataclass(frozen=True)
class ParamSpec:
    name: str
    type: str
    default: object = None
    required: bool = False
    min: float | None = None
    max: float | None = None


@dataclass(frozen=True)
class Rule:
    code: str
    version: int
    title: str
    severity: str
    indicative: bool
    description: str
    interpretation: str
    requires: tuple[str, ...]
    applicable_if: str | None
    params: tuple[ParamSpec, ...]
    message: str
    sql: str
    definition_hash: str = field(default="")

    def public(self) -> dict:
        return {"code": self.code, "version": self.version, "title": self.title, "severity": self.severity,
                "indicative": self.indicative, "description": self.description, "interpretation": self.interpretation,
                "requires": list(self.requires), "definition_hash": self.definition_hash,
                "params": [{"name": p.name, "type": p.type, "default": p.default, "required": p.required,
                            "min": p.min, "max": p.max} for p in self.params]}


def _load_one(path: Path) -> Rule:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or set(raw) - _KEYS:
        raise RuleError(f"{path.name} : clés inconnues {sorted(set(raw or {}) - _KEYS)}")
    for k in ("code", "version", "title", "severity", "description", "interpretation", "message", "sql"):
        if k not in raw:
            raise RuleError(f"{path.name} : « {k} » manquant")
    if not _CODE.fullmatch(str(raw["code"])) or path.stem != raw["code"]:
        raise RuleError(f"{path.name} : code invalide ou différent du nom de fichier")
    if not isinstance(raw["version"], int) or raw["version"] < 1:
        raise RuleError(f"{path.name} : version entière ≥ 1 attendue")
    if raw["severity"] not in ("info", "warning"):
        raise RuleError(f"{path.name} : gravité info|warning")
    req = tuple(raw.get("requires") or ())
    params = []
    for name, spec in (raw.get("params") or {}).items():
        if not re.fullmatch(r"[a-z_]{1,30}", str(name)) or spec.get("type") not in TYPES:
            raise RuleError(f"{path.name} : paramètre « {name} » invalide")
        params.append(ParamSpec(name, spec["type"], spec.get("default"), bool(spec.get("required")), spec.get("min"), spec.get("max")))
    sql = raw["sql"]
    if "{base}" not in sql and "has_error" not in sql:
        raise RuleError(f"{path.name} : une règle sans {{base}} doit filtrer has_error explicitement")
    if "{T}" not in sql or ("{base}" not in sql and "{doc}" not in sql):
        raise RuleError(f"{path.name} : le SQL doit lire {{T}} et filtrer par {{base}} ou {{doc}} (isolation par document)")
    used = set(re.findall(r"\{(\w+)\}", sql + raw["message"]))
    unknown = used - {"T", "base", "doc"} - {p.name for p in params} - {"n", "amount", "currency", "account", "reference", "entry_date",
                                                                          "source_rows", "span_days", "budget", "reason", "z", "debits",
                                                                          "credits", "fiscal_year", "window_days"}
    if unknown:
        raise RuleError(f"{path.name} : marqueurs inconnus {sorted(unknown)}")
    canon = json.dumps(raw, sort_keys=True, default=str, ensure_ascii=False)
    return Rule(raw["code"], raw["version"], raw["title"], raw["severity"], bool(raw.get("indicative")), raw["description"],
                raw["interpretation"], req, raw.get("applicable_if"), tuple(params), raw["message"], sql,
                hashlib.sha256(canon.encode()).hexdigest())


class RuleRegistry:
    def __init__(self, rules: dict[str, Rule]) -> None:
        self.rules = dict(sorted(rules.items()))

    def ruleset_hash(self) -> str:
        return hashlib.sha256("|".join(f"{r.code}:{r.version}:{r.definition_hash}" for r in self.rules.values()).encode()).hexdigest()


_cache: tuple[tuple, RuleRegistry] | None = None


def get_registry() -> RuleRegistry:
    """Registre en cache, rechargé si un fichier de règles change (date/taille)."""
    global _cache
    sig = tuple((f.name, f.stat().st_mtime_ns, f.stat().st_size) for f in sorted(DEFAULT_DIR.glob("AUD*.yaml")))
    if _cache is None or _cache[0] != sig:
        _cache = (sig, load_registry())
    return _cache[1]


def load_registry(directory: Path | None = None) -> RuleRegistry:
    d = directory or DEFAULT_DIR
    files = sorted(d.glob("AUD*.yaml"))
    if not files:
        raise RuleError(f"Aucune règle trouvée dans {d} (rules/ absent de l'image ?)")
    rules = {}
    for f in files:
        r = _load_one(f)
        rules[r.code] = r
    return RuleRegistry(rules)


# ── paramètres ──────────────────────────────────────────────────────────────

def _num(v, name: str, spec: ParamSpec, integer: bool):
    try:
        if isinstance(v, bool) or isinstance(v, float) and not integer or len(str(v)) > 40:
            raise ValueError
        d = Decimal(str(v))
    except (InvalidOperation, ValueError):
        raise ParamError(name, "nombre attendu") from None
    if not d.is_finite() or (integer and d != d.to_integral_value()):
        raise ParamError(name, "entier attendu" if integer else "nombre fini attendu")
    lo = Decimal(str(spec.min)) if spec.min is not None else -DEFAULT_MAX
    hi = Decimal(str(spec.max)) if spec.max is not None else DEFAULT_MAX      # plafond par défaut : jamais de littéral géant
    if d < lo or d > hi:
        raise ParamError(name, f"hors limites [{lo}, {hi}]")
    return int(d) if integer else d


def render_params(rule: Rule, given: dict | None) -> tuple[dict[str, str], dict]:
    """Valeurs validées → littéraux SQL sûrs. Retourne (littéraux, valeurs effectives pour la traçabilité)."""
    given = given or {}
    extra = set(given) - {p.name for p in rule.params}
    if extra:
        raise ParamError(sorted(extra)[0], "paramètre inconnu pour cette règle")
    lit: dict[str, str] = {}
    eff: dict = {}
    for p in rule.params:
        v = given.get(p.name, p.default)
        if v is None:
            raise ParamError(p.name, "paramètre obligatoire")
        if p.type == "int":
            n = _num(v, p.name, p, True)
            lit[p.name], eff[p.name] = str(n), n
        elif p.type == "decimal":
            n = _num(v, p.name, p, False)
            lit[p.name], eff[p.name] = format(n, "f"), format(n, "f")
        elif p.type == "date":
            try:
                d = date.fromisoformat(str(v))
            except ValueError:
                raise ParamError(p.name, "date ISO AAAA-MM-JJ attendue") from None
            lit[p.name], eff[p.name] = d.isoformat(), d.isoformat()
        elif p.type == "int_list":
            if not isinstance(v, list) or not 1 <= len(v) <= 7:
                raise ParamError(p.name, "liste de 1 à 7 entiers attendue")
            ns = sorted({_num(x, p.name, p, True) for x in v})
            lit[p.name], eff[p.name] = ", ".join(map(str, ns)), ns
        elif p.type == "budgets":
            if not isinstance(v, list) or not 1 <= len(v) <= MAX_BUDGETS:
                raise ParamError(p.name, f"liste de 1 à {MAX_BUDGETS} budgets attendue")
            rows, norm, seen = [], [], set()
            for b in v:
                if not isinstance(b, dict) or set(b) != {"account", "currency", "amount"}:
                    raise ParamError(p.name, "chaque budget = {account, currency, amount}")
                acc, ccy = str(b["account"]), str(b["currency"])
                if not _ACCOUNT.fullmatch(acc) or not _CCY.fullmatch(ccy):
                    raise ParamError(p.name, "compte ou devise invalide")
                if (acc, ccy) in seen:
                    raise ParamError(p.name, f"budget en double pour {acc}/{ccy}")
                seen.add((acc, ccy))
                amt = _num(b["amount"], p.name, ParamSpec("amount", "decimal", min=0, max=1e15), False)
                rows.append(f"('{acc}', '{ccy}', CAST({format(amt, 'f')} AS DECIMAL(38,6)))")
                norm.append({"account": acc, "currency": ccy, "amount": format(amt, "f")})
            lit[p.name] = f"(SELECT * FROM (VALUES {', '.join(rows)}) t(account, currency, budget))"
            eff[p.name] = norm
    return lit, eff

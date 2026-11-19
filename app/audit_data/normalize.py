"""Normalisation et contrôle qualité des données financières importées (P-074).

Principe : AUCUNE correction silencieuse. Une valeur qu'on ne comprend pas devient NULL dans la table normalisée ET une
anomalie listée (code, ligne, champ, valeur brute tronquée). Le séparateur décimal et le format de date sont DÉCLARÉS par
l'utilisateur (jamais devinés : 03/04/2026 est le 3 avril ou le 4 mars selon le pays) ; `suggest` ne fait que proposer.
Aucune devise implicite : une colonne ou une `default_currency` explicite est obligatoire.
"""
from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from app.audit_data.parse import Table

FIELDS = ("entry_date", "account", "label", "reference", "amount", "debit", "credit", "currency", "fiscal_year")
DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y/%m/%d")
DECIMAL_SEPARATORS = (".", ",")
MAX_SCALE = 6                 # DECIMAL(38,6) : au-delà, l'arrondi serait silencieux, donc refusé
AMOUNT_WARN = Decimal("1e13")
MAX_DIGITS = 30
MIN_YEAR, MAX_YEAR_AHEAD = 1990, 1
MAX_STORED_ISSUES = 5_000
CURRENCIES = frozenset("""AED AFN ALL AMD AOA ARS AUD AWG AZN BAM BBD BDT BGN BHD BIF BMD BND BOB BRL BSD BTN BWP BYN BZD CAD CDF CHF CLP
CNY COP CRC CUP CVE CZK DJF DKK DOP DZD EGP ERN ETB EUR FJD GBP GEL GHS GIP GMD GNF GTQ GYD HKD HNL HTG HUF IDR ILS INR IQD IRR ISK
JMD JOD JPY KES KGS KHR KMF KPW KRW KWD KYD KZT LAK LBP LKR LRD LSL LYD MAD MDL MGA MKD MMK MNT MOP MRU MUR MVR MWK MXN MYR MZN NAD
NGN NIO NOK NPR NZD OMR PAB PEN PGK PHP PKR PLN PYG QAR RON RSD RUB RWF SAR SBD SCR SDG SEK SGD SHP SLE SOS SRD SSP STN SVC SYP SZL
THB TJS TMT TND TOP TRY TTD TWD TZS UAH UGX USD UYU UZS VES VND VUV WST XAF XCD XOF XPF YER ZAR ZMW ZWL""".split())

_SYNONYMS = {
    "entry_date": ("date", "date ecriture", "date d ecriture", "date comptable", "entry date", "transaction date", "posting date"),
    "account": ("compte", "n compte", "numero compte", "code compte", "account", "account number", "gl account"),
    "label": ("libelle", "designation", "description", "label", "narrative", "objet"),
    "reference": ("reference", "ref", "piece", "n piece", "numero piece", "document", "voucher", "invoice"),
    "amount": ("montant", "amount", "valeur", "solde"),
    "debit": ("debit", "montant debit"),
    "credit": ("credit", "montant credit"),
    "currency": ("devise", "monnaie", "currency", "ccy"),
    "fiscal_year": ("exercice", "annee fiscale", "fiscal year", "annee"),
}
_TSEP = {".": "   ,'", ",": "   .'"}      # séparateurs de milliers tolérés selon le séparateur décimal déclaré


class OptionsError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ImportOptions:
    mapping: dict[str, str]                  # champ normalisé → en-tête du fichier
    decimal_separator: str
    date_format: str
    default_currency: str | None = None
    default_fiscal_year: int | None = None


@dataclass
class Issue:
    severity: str                            # "error" | "warning"
    code: str
    source_row: int | None
    field: str
    message: str
    raw_value: str = ""


@dataclass
class Record:
    source_row: int
    entry_date: date | None
    account: str | None
    label: str | None
    reference: str | None
    debit: Decimal | None
    credit: Decimal | None
    amount: Decimal | None
    currency: str | None
    currency_source: str                     # "column" | "default" | "none"
    fiscal_year: int | None
    has_error: bool


@dataclass
class Normalized:
    records: list[Record] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)          # plafonné à MAX_STORED_ISSUES
    counts: dict[str, int] = field(default_factory=dict)       # code → nombre total (non plafonné)
    totals: dict[str, str] = field(default_factory=dict)
    truncated: bool = False


# ── analyse de valeurs ───────────────────────────────────────────────────────

class ValueIssue(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def parse_amount(v, dec: str) -> Decimal | None:
    if v is None:
        return None
    if isinstance(v, bool) or isinstance(v, (date, datetime)):
        raise ValueIssue("non_numeric_amount", "Ce n'est pas un montant.")
    if isinstance(v, int):
        out = Decimal(v)
    elif isinstance(v, float):
        if not math.isfinite(v):
            raise ValueIssue("non_numeric_amount", "Montant non fini.")
        out = Decimal(repr(v))        # forme la plus courte qui redonne le même flottant (celle saisie dans Excel)
    elif isinstance(v, Decimal):
        if not v.is_finite():
            raise ValueIssue("non_numeric_amount", "Montant non fini.")
        out = v
    else:
        s = str(v).strip()
        neg = False
        if s.startswith("(") and s.endswith(")"):
            neg, s = True, s[1:-1].strip()
        if s[:1] in ("+", "-"):
            neg ^= s[0] == "-"
            s = s[1:].strip()
        tsep = re.escape(_TSEP[dec])
        m = re.match(rf"^(\d{{1,3}}(?:[{tsep}]\d{{3}})+|\d+)(?:{re.escape(dec)}(\d+))?$", s, re.ASCII)
        if not m:
            raise ValueIssue("non_numeric_amount", f"Format de montant non reconnu (séparateur décimal déclaré : « {dec} »).")
        whole, frac = m.group(1), m.group(2) or ""
        if len({c for c in whole if not c.isdigit()}) > 1:
            raise ValueIssue("non_numeric_amount", "Séparateurs de milliers incohérents.")
        digits = re.sub(r"\D", "", whole)
        out = Decimal(f"{digits}.{frac}" if frac else digits)
        out = -out if neg else out
    if len(out.as_tuple().digits) > MAX_DIGITS:
        raise ValueIssue("amount_out_of_range", "Montant avec trop de chiffres.")
    if -out.as_tuple().exponent > MAX_SCALE and out != out.quantize(Decimal(1).scaleb(-MAX_SCALE)):
        raise ValueIssue("too_many_decimals", f"Plus de {MAX_SCALE} décimales : arrondi refusé (il serait silencieux).")
    return out


def parse_date(v, fmt: str) -> date:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, (int, float, Decimal)):
        raise ValueIssue("invalid_date", "Nombre au lieu d'une date (cellule non formatée en date).")
    s = str(v).strip()
    if len(s) > 20:
        raise ValueIssue("invalid_date", "Date illisible.")
    try:
        return datetime.strptime(s, fmt).date()
    except ValueError:
        raise ValueIssue("invalid_date", f"Date non conforme au format déclaré ({fmt}).") from None


def _plain(v) -> str | None:
    if v is None:
        return None
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    return str(v).strip() or None


def _fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


# ── suggestions (jamais appliquées sans validation) ─────────────────────────

def suggest(table: Table) -> dict:
    folded = {h: _fold(h) for h in table.headers}
    mapping: dict[str, str] = {}
    used: set[str] = set()
    for f, syns in _SYNONYMS.items():
        for h, fh in folded.items():
            if h not in used and fh in syns:
                mapping[f] = h
                used.add(h)
                break
    sample = table.rows[:200]
    idx = {h: i for i, h in enumerate(table.headers)}
    comma = dot = 0
    for f in ("amount", "debit", "credit"):
        if f in mapping:
            for _, cells in sample:
                v = cells[idx[mapping[f]]]
                if isinstance(v, str):
                    comma += bool(re.search(r",\d{1,2}$", v))
                    dot += bool(re.search(r"\.\d{1,2}$", v))
    sep = "," if comma > dot else "." if dot > comma else None
    fmts: list[str] = []
    if "entry_date" in mapping:
        vals = [c[idx[mapping["entry_date"]]] for _, c in sample if c[idx[mapping["entry_date"]]] is not None]
        if vals and not all(isinstance(v, (date, datetime)) for v in vals):
            for fmt in DATE_FORMATS:
                try:
                    for v in vals:
                        parse_date(v, fmt)
                    fmts.append(fmt)
                except ValueIssue:
                    pass
    return {"mapping": mapping, "decimal_separator": sep, "date_formats": fmts,
            "note": "Suggestions à vérifier : plusieurs formats de date possibles = choix humain obligatoire."}


# ── validation des options ──────────────────────────────────────────────────

def validate_options(table: Table, o: ImportOptions) -> None:
    unknown = set(o.mapping) - set(FIELDS)
    if unknown:
        raise OptionsError("unknown_field", f"Champ(s) inconnu(s) : {', '.join(sorted(unknown))}.")
    missing_cols = [c for c in o.mapping.values() if c not in table.headers]
    if missing_cols:
        raise OptionsError("unknown_column", f"Colonne(s) absente(s) du fichier : {', '.join(map(str, missing_cols[:5]))}.")
    if len(set(o.mapping.values())) != len(o.mapping):
        raise OptionsError("column_reused", "Une même colonne ne peut pas alimenter deux champs.")
    for req in ("entry_date", "account"):
        if req not in o.mapping:
            raise OptionsError("missing_mapping", f"Colonne obligatoire non associée : {req}.")
    has_amount = "amount" in o.mapping
    has_dc = "debit" in o.mapping or "credit" in o.mapping
    if not has_amount and not has_dc:
        raise OptionsError("missing_mapping", "Associez « amount » ou « debit »/« credit ».")
    if has_amount and has_dc:
        raise OptionsError("amount_ambiguous", "« amount » et « debit »/« credit » ensemble sont ambigus : choisissez l'un des deux.")
    if o.decimal_separator not in DECIMAL_SEPARATORS:
        raise OptionsError("decimal_separator_required", "Séparateur décimal à déclarer explicitement (« . » ou « , »).")
    if o.date_format not in DATE_FORMATS:
        raise OptionsError("date_format_required", f"Format de date à déclarer explicitement parmi : {', '.join(DATE_FORMATS)}.")
    if "currency" not in o.mapping and not o.default_currency:
        raise OptionsError("currency_required", "Devise obligatoire : associez une colonne « currency » ou indiquez une devise par défaut explicite.")
    if o.default_currency is not None and o.default_currency not in CURRENCIES:
        raise OptionsError("unknown_currency", f"Devise par défaut inconnue : {o.default_currency[:8]!r} (code ISO 4217 attendu).")
    if o.default_fiscal_year is not None and not MIN_YEAR <= o.default_fiscal_year <= 2100:
        raise OptionsError("invalid_fiscal_year", "Exercice par défaut hors limites.")


# ── normalisation ───────────────────────────────────────────────────────────

def normalize(table: Table, o: ImportOptions) -> Normalized:
    validate_options(table, o)
    idx = {f: table.headers.index(h) for f, h in o.mapping.items()}
    out = Normalized()
    today_year = date.today().year
    seen: dict[tuple, int] = {}
    sum_debit = sum_credit = Decimal(0)

    def add(i: Issue) -> None:
        out.counts[i.code] = out.counts.get(i.code, 0) + 1
        if len(out.issues) < MAX_STORED_ISSUES:
            out.issues.append(i)
        else:
            out.truncated = True

    for n, cells in table.rows:
        errors = 0

        def issue(sev: str, code: str, fld: str, msg: str, raw=None, n=n) -> None:
            nonlocal errors
            errors += sev == "error"
            add(Issue(sev, code, n, fld, msg, "" if raw is None else str(raw)[:100]))

        def cell(f: str):
            return cells[idx[f]] if f in idx else None

        d = None
        if cell("entry_date") is None:
            issue("error", "missing_value", "entry_date", "Date manquante.")
        else:
            try:
                d = parse_date(cell("entry_date"), o.date_format)
                if d.year < MIN_YEAR or d.year > today_year + MAX_YEAR_AHEAD:
                    issue("warning", "date_out_of_range", "entry_date", f"Date hors de la plage plausible ({MIN_YEAR}–{today_year + MAX_YEAR_AHEAD}).", d)
            except ValueIssue as e:
                issue("error", e.code, "entry_date", str(e), cell("entry_date"))
        account = _plain(cell("account"))
        if account is None:
            issue("error", "missing_value", "account", "Compte manquant.")
        amounts: dict[str, Decimal | None] = {}
        for f in ("amount", "debit", "credit"):
            if f not in idx:
                continue
            try:
                amounts[f] = parse_amount(cell(f), o.decimal_separator)
                if amounts[f] is not None and abs(amounts[f]) >= AMOUNT_WARN:
                    issue("warning", "amount_out_of_range", f, "Montant exceptionnellement élevé.", amounts[f])
            except ValueIssue as e:
                amounts[f] = None
                issue("error", e.code, f, str(e), cell(f))
        raw_present = any(cell(f) is not None for f in amounts)
        if not raw_present:
            issue("error", "missing_value", "amount", "Aucun montant sur la ligne.")
        debit, credit = amounts.get("debit"), amounts.get("credit")
        if "amount" in amounts:
            amount = amounts["amount"]
        elif debit is not None or credit is not None:
            amount = (debit or Decimal(0)) - (credit or Decimal(0))        # convention : débit positif, crédit négatif
        else:
            amount = None
        sum_debit += debit or 0
        sum_credit += credit or 0

        currency, csrc = None, "none"
        raw_ccy = _plain(cell("currency")) if "currency" in idx else None
        if raw_ccy is not None:
            currency, csrc = raw_ccy.upper(), "column"
            if currency not in CURRENCIES:
                issue("error", "unknown_currency", "currency", "Devise inconnue (code ISO 4217 attendu).", raw_ccy)
                currency = None
        elif o.default_currency:
            currency, csrc = o.default_currency, "default"
        else:
            issue("error", "missing_currency", "currency", "Devise manquante sur la ligne (aucune devise par défaut déclarée).")

        fy = o.default_fiscal_year
        if "fiscal_year" in idx and cell("fiscal_year") is not None:
            raw_fy = _plain(cell("fiscal_year"))
            if raw_fy and re.fullmatch(r"[0-9]{4}", raw_fy) and MIN_YEAR <= int(raw_fy) <= 2100:
                fy = int(raw_fy)
            else:
                fy = None
                issue("error", "invalid_fiscal_year", "fiscal_year", "Exercice invalide (année à 4 chiffres attendue).", cell("fiscal_year"))

        label, ref = _plain(cell("label")), _plain(cell("reference"))
        key = (d, account, label, ref, debit, credit, amount, currency)
        if key in seen and errors == 0:
            issue("warning", "duplicate_row", "*", f"Ligne identique à la ligne {seen[key]}.")
        else:
            seen.setdefault(key, n)
        out.records.append(Record(n, d, account, label, ref, debit, credit, amount, currency, csrc, fy, errors > 0))

    if "debit" in idx and "credit" in idx and sum_debit != sum_credit:
        add(Issue("warning", "totals_mismatch", None, "*",
                  f"Total des débits ({sum_debit}) différent du total des crédits ({sum_credit}) : écart {sum_debit - sum_credit}."))
    out.totals = {"debit": str(sum_debit), "credit": str(sum_credit)} if "debit" in idx and "credit" in idx else {}
    return out

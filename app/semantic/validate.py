"""Validation d'un modèle sémantique (P-065) : une définition fausse est répétée partout.

Retourne une liste de problèmes sans jamais lever : l'appelant décide quoi en faire
(route d'administration, test, CI).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import sqlglot
from sqlglot import exp

from app.semantic.model import SemanticModel
from app.semantic.resolver import normalize


# Codelist SDMX CL_FREQ (périodicités usuelles)
SDMX_FREQUENCIES = {"A": "annuelle", "S": "semestrielle", "Q": "trimestrielle", "M": "mensuelle",
                    "W": "hebdomadaire", "D": "quotidienne", "H": "horaire", "B": "jours ouvrés", "N": "à la minute"}
_CODE_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True)
class Issue:
    level: str     # "error" | "warning"
    code: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"level": self.level, "code": self.code, "message": self.message}


def _columns_of(sql: str) -> tuple[list[exp.Column], str | None]:
    try:
        tree = sqlglot.parse_one(sql, read="duckdb")
    except Exception as e:  # noqa: BLE001 - tout échec d'analyse est un problème de modèle
        return [], f"SQL illisible : {str(e).splitlines()[0][:120]}"
    return list(tree.find_all(exp.Column)), None


def validate_model(model: SemanticModel) -> list[Issue]:
    issues: list[Issue] = []
    table_cols = {t.name: {c.name for c in t.columns} for t in model.tables}
    every_col = set().union(*table_cols.values()) if table_cols else set()

    # 1. Noms uniques par type
    for label, names in (
        ("table", [t.name for t in model.tables]),
        ("mesure", [m.name for m in model.metrics]),
        ("filtre", [f.name for f in model.filters]),
    ):
        seen: dict[str, str] = {}
        for n in names:
            k = normalize(n)
            if k in seen:
                issues.append(Issue("error", "duplicate_name", f"{label} en double : « {n} » et « {seen[k]} »"))
            seen[k] = n

    # 2. Mesures et filtres : tables, SQL, colonnes
    def check_sql(kind: str, name: str, sql: str, tables: list[str]) -> None:
        for t in tables:
            if t not in table_cols:
                issues.append(Issue("error", "unknown_table", f"{kind} « {name} » : table inconnue « {t} »"))
        cols, err = _columns_of(sql)
        if err:
            issues.append(Issue("error", "bad_sql", f"{kind} « {name} » : {err}"))
            return
        declared = set().union(*(table_cols.get(t, set()) for t in tables)) if tables else every_col
        for c in cols:
            if c.table:
                if c.name not in every_col:
                    issues.append(Issue("error", "unknown_column", f"{kind} « {name} » : colonne inconnue « {c.table}.{c.name} »"))
            elif c.name not in declared:
                level = "error" if c.name not in every_col else "warning"
                msg = (f"{kind} « {name} » : colonne « {c.name} » inconnue du modèle" if level == "error"
                       else f"{kind} « {name} » : colonne « {c.name} » absente des tables déclarées")
                issues.append(Issue(level, "unknown_column" if level == "error" else "column_outside_tables", msg))

    for m in model.metrics:
        check_sql("mesure", m.name, m.sql, m.tables)
        if not m.description.strip():
            issues.append(Issue("warning", "no_description", f"mesure « {m.name} » sans description"))
    for f in model.filters:
        check_sql("filtre", f.name, f.sql, f.tables)

    # 2b. Métadonnées d'indicateur (P-066)
    codes: dict[str, str] = {}
    for m in model.metrics:
        if m.code:
            if not _CODE_RE.match(m.code):
                issues.append(Issue("error", "bad_indicator_code", f"mesure « {m.name} » : code « {m.code} » invalide (A-Z, 0-9 et _, commence par une lettre)"))
            elif m.code in codes:
                issues.append(Issue("error", "duplicate_indicator_code", f"code « {m.code} » utilisé par « {codes[m.code]} » et « {m.name} »"))
            codes[m.code] = m.name
        if m.frequency and m.frequency not in SDMX_FREQUENCIES:
            issues.append(Issue("error", "bad_frequency", f"mesure « {m.name} » : périodicité « {m.frequency} » inconnue (attendu : {', '.join(SDMX_FREQUENCIES)})"))
        if m.last_updated and not _DATE_RE.match(m.last_updated):
            issues.append(Issue("error", "bad_date", f"mesure « {m.name} » : last_updated « {m.last_updated} » doit être AAAA-MM-JJ"))
        if m.code and not m.source.strip():
            issues.append(Issue("warning", "indicator_without_source", f"indicateur « {m.code} » sans source"))
        if m.code and not (m.definition.strip() or m.description.strip()):
            issues.append(Issue("warning", "indicator_without_definition", f"indicateur « {m.code} » sans définition"))

    # 2c. Mesures liées à une formule du registre financier (P-073) : la formule doit exister
    if any(m.formula for m in model.metrics):
        from app.financial.registry import RegistryError, get_registry
        try:
            known = set(get_registry().codes())
        except RegistryError as e:
            known = None
            issues.append(Issue("error", "formula_registry_unavailable", f"registre de formules illisible : {e}"))
        for m in model.metrics:
            if m.formula and known is not None and m.formula not in known:
                issues.append(Issue("error", "unknown_formula", f"mesure « {m.name} » : formule « {m.formula} » absente du registre"))

    # 3. Synonymes de valeurs : table et colonne existantes
    for v in model.value_synonyms:
        if v.table not in table_cols:
            issues.append(Issue("error", "unknown_table", f"synonymes de « {v.value} » : table inconnue « {v.table} »"))
        elif v.column not in table_cols[v.table]:
            issues.append(Issue("error", "unknown_column", f"synonymes de « {v.value} » : colonne inconnue « {v.table}.{v.column} »"))

    # 4. Alias ambigus : une même expression ne doit pas désigner deux choses différentes
    owners: dict[str, set[str]] = {}

    def own(label: str, owner: str) -> None:
        k = normalize(label)
        if k:
            owners.setdefault(k, set()).add(owner)

    for m in model.metrics:
        for label in [m.name, *m.aliases]:
            own(label, f"mesure « {m.name} »")
    for f in model.filters:
        for label in [f.name, *f.aliases]:
            own(label, f"filtre « {f.name} »")
    for t in model.tables:
        for c in t.columns:
            for label in c.aliases:
                own(label, f"colonne {t.name}.{c.name}")
    for v in model.value_synonyms:
        for label in [v.value, *v.synonyms]:
            own(label, f"valeur {v.table}.{v.column}='{v.value}'")
    for k, who in sorted(owners.items()):
        if len(who) > 1:
            issues.append(Issue("error", "ambiguous_alias", f"« {k} » désigne plusieurs objets : " + " ; ".join(sorted(who))))

    return issues

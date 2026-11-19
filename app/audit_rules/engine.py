"""Exécution déterministe des règles d'audit (P-075) : SQL paramétré via `DataStore.execute` (sécurité par ligne, D-3).

Une règle ne conclut jamais : elle produit des « signaux de risque à examiner » rattachés à une règle et à sa version.
Une règle dont les données manquent est `not_applicable` avec la raison (jamais « aucun problème » par défaut).
"""
from __future__ import annotations

import json
import threading
from dataclasses import dataclass

import duckdb

from app.audit_data import repo
from app.audit_rules.registry import ParamError, Rule, RuleRegistry, render_params

MAX_FINDINGS_PER_RULE = 500
MAX_RECORD_REFS = 50
RULE_TIMEOUT_S = 20.0


@dataclass
class RuleOutcome:
    code: str
    version: int
    status: str                  # "ran" | "not_applicable" | "error"
    reason: str = ""
    findings: list[dict] = None
    truncated: bool = False
    params: dict = None


class _Safe(dict):
    def __missing__(self, key):
        return "?"


def _missing_fields(doc: dict, needs: tuple[str, ...]) -> list[str]:
    """Champs exigés par la règle qui n'ont PAS été associés à une colonne à l'import (une colonne associée mais vide
    reste exploitable : c'est précisément ce que certaines règles signalent)."""
    mapped = set(((doc.get("options") or {}).get("mapping") or {}))
    return [c for c in needs if c not in mapped and not (c == "amount" and {"debit", "credit"} & mapped)]


def run_rule(store, rule: Rule, doc: dict, params: dict | None) -> RuleOutcome:
    doc_id = doc["document_id"]
    if not repo.valid_id(doc_id):
        raise ValueError("document_id invalide")
    try:
        lit, eff = render_params(rule, params)
    except ParamError as e:
        return RuleOutcome(rule.code, rule.version, "not_applicable", f"paramètre : {e}", [], params={})
    missing = _missing_fields(doc, rule.requires)
    if missing:
        return RuleOutcome(rule.code, rule.version, "not_applicable",
                           f"données absentes : {', '.join(missing)}", [], params=eff)
    if rule.applicable_if and not store.execute(
            f"SELECT count(*) FROM {repo.RECORDS} WHERE document_id = '{doc_id}' AND ({rule.applicable_if})")[1][0][0]:
        return RuleOutcome(rule.code, rule.version, "not_applicable", "aucune donnée exploitable pour cette règle", [], params=eff)
    sql = rule.sql.format_map(_Safe(T=repo.RECORDS, doc=doc_id, base=f"document_id = '{doc_id}' AND has_error = FALSE", **lit))
    timer = threading.Timer(RULE_TIMEOUT_S, store.con.interrupt)      # une règle trop lente est interrompue, pas subie
    timer.start()
    try:
        cols, rows = store.execute(f"SELECT * FROM ({sql}) ORDER BY source_rows LIMIT {MAX_FINDINGS_PER_RULE + 1}")
    except duckdb.InterruptException:
        return RuleOutcome(rule.code, rule.version, "error", f"délai dépassé ({RULE_TIMEOUT_S} s) : règle interrompue", [], params=eff)
    except (duckdb.Error, PermissionError, ValueError) as e:
        return RuleOutcome(rule.code, rule.version, "error", f"{type(e).__name__}", [], params=eff)
    finally:
        timer.cancel()
    if "source_rows" not in cols:
        return RuleOutcome(rule.code, rule.version, "error", "colonne source_rows absente", [], params=eff)
    truncated = len(rows) > MAX_FINDINGS_PER_RULE
    seen, findings = set(), []
    for r in rows[:MAX_FINDINGS_PER_RULE]:
        d = {c: ("" if v is None else str(v)) for c, v in zip(cols, r, strict=True)}
        if d["source_rows"] in seen:
            continue
        seen.add(d["source_rows"])
        refs = [int(x) for x in d["source_rows"].split(",") if x.strip().isdigit()][:MAX_RECORD_REFS]
        msg = rule.message.format_map(_Safe(d))
        prefix = "Indicatif seulement — " if rule.indicative else "Signal de risque à examiner — "
        findings.append({"summary": prefix + msg, "source_rows": refs, "amount": d.get("amount") or None,
                         "details": json.dumps(d, ensure_ascii=False, sort_keys=True)})
    return RuleOutcome(rule.code, rule.version, "ran", "", findings, truncated, eff)


def run_rules(store, registry: RuleRegistry, doc: dict, params: dict[str, dict] | None, codes: list[str] | None) -> list[RuleOutcome]:
    params = params or {}
    selected = list(dict.fromkeys(codes or registry.rules))      # doublons ignorés
    unknown = [c for c in selected if c not in registry.rules]
    if unknown:
        raise KeyError(unknown[0])
    stray = set(params) - set(registry.rules)
    if stray:
        raise KeyError(sorted(stray)[0])
    return [run_rule(store, registry.rules[c], doc, params.get(c)) for c in selected]

"""Routage d'une question du chat vers le moteur de formules (P-080, décision D-2).

Règle : un chiffre est « Calculé » seulement s'il sort du moteur versionné (P-073) ; tout le reste est
« Exploratoire, non certifié ». Le modèle de langage n'intervient PAS ici :
  - la reconnaissance de la question est déterministe (résolveur sémantique P-065) ;
  - les paramètres viennent de liens déclarés dans `semantic/model.yaml` (`formula_inputs`), jamais devinés ;
  - la réponse est rédigée localement (aucune donnée envoyée à un modèle, donc compatible avec le mode strict) ;
  - l'ensemble des actions possibles est une liste blanche de UNE fonction (`perform_run`) : ni SQL ni
    commande fournis par un modèle ou par un document importé.
Dans le doute (aucune mesure liée, plusieurs formules possibles), on renvoie None : réponse exploratoire.
"""
from __future__ import annotations

import re
from decimal import Decimal

from pydantic import ValidationError

from app.financial.engine import CalculationError
from app.financial.registry import RegistryError, get_registry
from app.financial.service import TableBinding, perform_run
from app.security import row_policy
from app.security.actor import audit_soft
from app.financial.trusted import untrusted_reason
from app.semantic.resolver import normalize, resolve_terms

CALCULATED = "calculated"
EXPLORATORY = "exploratory"
UNAVAILABLE = "formula_unavailable"      # question reconnue mais aucun chiffre produit : jamais de pastille « Calculé »

LABELS = {
    CALCULATED: "Calculé",
    EXPLORATORY: "Exploratoire, non certifié",
    UNAVAILABLE: "Calcul non effectué",
}


def format_number(canonical_value: str) -> str:
    """« 1234567.5 » → « 1 234 567,5 » (espace fine insécable, virgule décimale)."""
    d = Decimal(canonical_value)
    sign = "-" if d < 0 else ""
    whole, _, frac = format(abs(d), "f").partition(".")
    grouped = f"{int(whole):,}".replace(",", " ")
    return f"{sign}{grouped}{',' + frac if frac else ''}"


# Codes dont le message détaille le schéma (table, colonne, type) : le chat n'affiche qu'un texte générique,
# le détail reste dans le journal d'audit (revue sécurité P-080, FAIBLE-1).
_SCHEMA_CODES = {"unknown_table", "unknown_column", "unsupported_column", "aggregation_failed", "unknown_variable", "duplicate_source"}


def _blocked(message: str, **extra) -> dict:
    return {"provenance": UNAVAILABLE, "answer": message, "error": None, **extra}


_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
_MAX_SHOWN = 8


def _scope_value(store, table: str, column: str, question: str):
    """Valeur de la dimension citée dans la question : (valeur, None) ou (None, valeurs possibles).

    Les valeurs candidates viennent des données (lecture par `DataStore.execute`, sécurité par ligne). Une valeur est
    retenue seulement si UNE SEULE valeur existante apparaît dans la question ; aucune ou plusieurs : on demande."""
    _, rows = store.execute(f'SELECT DISTINCT "{column}" FROM "{table}" WHERE "{column}" IS NOT NULL ORDER BY 1 LIMIT 500')
    values = [r[0] for r in rows]
    q = normalize(question).split()
    hits = []
    for v in values:
        vt = normalize(str(v)).split()
        if vt and any(q[i:i + len(vt)] == vt for i in range(len(q) - len(vt) + 1)):
            hits.append((v, vt))
    hits = [h for h in hits if not any(h is not o and len(o[1]) > len(h[1]) and any(o[1][i:i + len(h[1])] == h[1] for i in range(len(o[1]) - len(h[1]) + 1)) for o in hits)]
    if len(hits) == 1:
        v = hits[0][0]
        return (v if isinstance(v, int | str) and not isinstance(v, bool) else str(v)), None
    return None, [str(v) for v in values[:_MAX_SHOWN]]


def route_formula(model, question: str, store, *, actor: str, role: str) -> dict | None:
    """None → chemin exploratoire (text-to-SQL). Sinon dict de réponse (calculée ou bloquée, avec la raison)."""
    if model is None or not question or not store.tables:
        return None          # pas de donnée chargée : le chemin exploratoire donne le message habituel
    linked = [t for t in resolve_terms(model, question) if t.kind == "metric"]
    metrics = {m.name: m for m in model.metrics}
    candidates = {metrics[t.target].formula: metrics[t.target] for t in linked if t.target in metrics and metrics[t.target].formula}
    if len(candidates) != 1:
        return None          # aucune formule, ou plusieurs : on ne choisit pas, réponse exploratoire
    code, metric = next(iter(candidates.items()))
    try:
        fv = get_registry().get(code)
    except RegistryError:
        return _blocked("La formule liée à cette mesure est introuvable dans le registre : aucun chiffre calculé.")
    base = {"formula": {"code": fv.code, "version": fv.version, "label": fv.label}}

    if role not in ("editor", "admin"):
        audit_soft("chat_formula_refused", formula=fv.code, reason="role", actor=actor)
        return _blocked(f"« {fv.label} » se calcule avec la formule {fv.code} v{fv.version}, mais lancer un calcul est réservé "
                        "aux éditeurs. Aucun chiffre n'est donné ici.", **base)

    missing = [v for v in fv.variables if v.required and v.name not in metric.formula_inputs]
    if missing:
        names = ", ".join(f"{v.label} ({v.name})" for v in missing)
        return _blocked(f"Pour calculer « {fv.label} » ({fv.code} v{fv.version}), il manque : {names}. "
                        "Renseignez-les dans l'écran Formules ; je ne les devine pas.", missing=[v.name for v in missing], **base)

    tables = sorted({b["table"] for b in metric.formula_inputs.values()})
    if not tables or not all(_IDENT.match(t) for t in tables):
        return _blocked("Configuration de la mesure invalide : aucun chiffre calculé.", **base)
    for t in tables:       # « Calculé » : jamais depuis une table déposée par un utilisateur
        reason = untrusted_reason(store, t)
        if reason:
            audit_soft("chat_formula_refused", formula=fv.code, reason="untrusted_source", actor=actor)
            return _blocked(f"« {fv.label} » n'est pas calculé : {reason}. Aucun chiffre « Calculé » n'est donné.", **base)

    scope: dict[str, str | int] = {}
    asks: list[str] = []
    try:
        for dim in metric.formula_scope:
            col = dim["column"]
            if not _IDENT.match(col):
                return _blocked("Configuration de la mesure invalide : aucun chiffre calculé.", **base)
            val, options = _scope_value(store, tables[0], col, question)
            if val is None:
                asks.append(f"{dim['label']} (valeurs possibles : {', '.join(options)})" if options else dim["label"])
            else:
                scope[col] = val
    except row_policy.AccessDenied:
        return _blocked("Accès refusé aux données nécessaires à ce calcul.", reason="access_denied", **base)
    except Exception as exc:       # colonne ou table absente des données chargées : on ne devine pas, on n'invente rien
        audit_soft("chat_formula_refused", formula=fv.code, reason="scope_unreadable", error=type(exc).__name__, actor=actor)
        return _blocked("Les dimensions de cette mesure sont introuvables dans les données chargées : aucun chiffre calculé.", **base)
    if asks:
        return _blocked(f"Pour calculer « {fv.label} » ({fv.code} v{fv.version}), précisez : {' ; '.join(asks)}. "
                        "Je ne choisis pas à votre place.", missing_scope=[d["column"] for d in metric.formula_scope if d["column"] not in scope], **base)

    try:
        bindings = {name: TableBinding(table=b["table"], column=b["column"], agg=b.get("agg", "sum"),
                                       where={**scope, **(b.get("filters") or {})})
                    for name, b in metric.formula_inputs.items()}
    except ValidationError:
        return _blocked("Configuration de la mesure invalide (filtre ou agrégation) : aucun chiffre calculé.", **base)
    try:
        run = perform_run(store, actor=actor, is_admin=role == "admin", formula_code=fv.code, version=fv.version,
                          inputs={}, from_table=bindings, via="chat")
    except CalculationError as e:
        detail = "les données liées à cette mesure sont indisponibles ou inadaptées (voir le journal)" if e.code in _SCHEMA_CODES else str(e)
        return _blocked(f"Calcul impossible pour « {fv.label} » : {detail}", reason=e.code, **base)
    except row_policy.AccessDenied:
        return _blocked("Accès refusé aux données nécessaires à ce calcul.", reason="access_denied", **base)
    except RegistryError:
        return _blocked("Formule introuvable dans le registre : aucun chiffre calculé.", **base)

    res = run["result"] or {}
    unit = f" {fv.result_unit}" if fv.result_unit else ""
    if res.get("status") != "ok" or res.get("value") is None:
        return _blocked(f"« {fv.label} » : {res.get('message') or 'résultat indéfini'} Aucun chiffre n'est affiché.",
                        run_id=run["run_id"], **base)
    audit_soft("chat_formula_answer", formula=fv.code, version=fv.version, run_id=run["run_id"], actor=actor)
    return {
        "provenance": CALCULATED,
        "answer": f"{fv.label}{(' (' + ', '.join(f'{k} = {v}' for k, v in scope.items()) + ')') if scope else ''} : "
                  f"{format_number(res['value'])}{unit}. Formule {fv.code} v{fv.version}, run {run['run_id']}.",
        "error": None, "run_id": run["run_id"], "value": res["value"], "unit": fv.result_unit,
        "inputs": run["inputs"], "scope": scope, **base,
    }

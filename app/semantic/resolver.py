"""Résolution déterministe des termes métier d'une question (P-065).

Avant d'appeler le LLM, on repère dans la question les noms et synonymes déclarés dans le
modèle sémantique (mesures, filtres nommés, colonnes, valeurs) et on les injecte dans le
prompt avec leur définition exacte. Ainsi « le CA au QC pour les ventes confirmées »
reçoit toujours la même définition, quelle que soit la formulation, sans dépendre d'un
modèle de similarité.

Règles de correspondance :
- insensible à la casse, aux accents, à l'apostrophe et au pluriel simple (s / x) ;
- les expressions les plus longues l'emportent, sans chevauchement ;
- un synonyme de 3 caractères ou moins (« CA », « QC ») ne correspond que s'il est écrit
  exactement ainsi dans la question : « ça » ne doit pas devenir « CA ».
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from app.semantic.model import SemanticModel

_TOKEN_RE = re.compile(r"[0-9A-Za-zÀ-ÿ]+")
_SHORT = 3


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def _stem(token: str) -> str:
    """Pluriel simple : « ventes » = « vente », « chevaux » non géré (volontairement)."""
    t = token
    if len(t) > 3 and t.endswith(("s", "x")):
        t = t[:-1]
    return t


def normalize(text: str) -> str:
    """Forme de comparaison : sans accents, minuscules, mots racinisés, séparés par un espace."""
    toks = _TOKEN_RE.findall(_strip_accents(text).lower())
    return " ".join(_stem(t) for t in toks)


@dataclass(frozen=True)
class ResolvedTerm:
    kind: str          # "metric" | "filter" | "column" | "value"
    matched: str       # texte trouvé dans la question
    target: str        # nom canonique (mesure, filtre, table.colonne)
    definition: str    # SQL ou valeur à utiliser
    detail: str = ""   # information complémentaire (unité, description)


@dataclass
class _Entry:
    phrase: tuple[str, ...]   # tokens normalisés
    exact: str | None         # forme exacte exigée pour les synonymes courts
    term_kind: str
    target: str
    definition: str
    detail: str


def _entries(model: SemanticModel) -> list[_Entry]:
    out: list[_Entry] = []

    def add(label: str, kind: str, target: str, definition: str, detail: str = "") -> None:
        label = label.strip()
        if not label:
            return
        norm = normalize(label)
        if not norm:
            return
        short = len(norm.replace(" ", "")) <= _SHORT
        out.append(_Entry(tuple(norm.split()), label if short else None, kind, target, definition, detail))

    for m in model.metrics:
        for label in [m.name, *m.aliases]:
            add(label, "metric", m.name, m.sql, " ; ".join(x for x in (m.unit, m.description) if x))
    for f in model.filters:
        for label in [f.name, *f.aliases]:
            add(label, "filter", f.name, f.sql, f.description)
    for t in model.tables:
        for c in t.columns:
            for label in c.aliases:
                add(label, "column", f"{t.name}.{c.name}", f"{t.name}.{c.name}", c.description)
    for v in model.value_synonyms:
        for label in [v.value, *v.synonyms]:
            add(label, "value", f"{v.table}.{v.column}", f"{v.table}.{v.column} = '{v.value}'")
    return out


def resolve_terms(model: SemanticModel | None, question: str) -> list[ResolvedTerm]:
    """Termes du modèle présents dans la question, dans l'ordre d'apparition."""
    if model is None or not question:
        return []
    entries = _entries(model)
    if not entries:
        return []

    raw_tokens = _TOKEN_RE.findall(question)
    norm_tokens = [_stem(_strip_accents(t).lower()) for t in raw_tokens]
    by_len = sorted(entries, key=lambda e: len(e.phrase), reverse=True)
    taken = [False] * len(norm_tokens)
    found: list[tuple[int, ResolvedTerm]] = []

    for e in by_len:
        n = len(e.phrase)
        for i in range(len(norm_tokens) - n + 1):
            if any(taken[i:i + n]) or tuple(norm_tokens[i:i + n]) != e.phrase:
                continue
            matched = " ".join(raw_tokens[i:i + n])
            if e.exact is not None and matched != e.exact:
                continue
            for k in range(i, i + n):
                taken[k] = True
            found.append((i, ResolvedTerm(e.term_kind, matched, e.target, e.definition, e.detail)))

    found.sort(key=lambda x: x[0])
    # un même objet reconnu plusieurs fois n'est listé qu'une fois
    seen: set[tuple[str, str]] = set()
    out: list[ResolvedTerm] = []
    for _, t in found:
        key = (t.kind, t.target if t.kind != "value" else t.definition)
        if key not in seen:
            seen.add(key)
            out.append(t)
    return out


_LABEL = {"metric": "mesure", "filter": "filtre (WHERE)", "column": "colonne", "value": "valeur"}


def format_resolved(terms: list[ResolvedTerm]) -> str:
    """Bloc de prompt listant les définitions exactes des termes reconnus."""
    if not terms:
        return ""
    lines = ["Termes reconnus dans la question (utilise exactement ces définitions) :"]
    for t in terms:
        extra = f" — {t.detail}" if t.detail else ""
        if t.kind == "metric":
            lines.append(f"- « {t.matched} » → mesure « {t.target} » = {t.definition}{extra}")
        elif t.kind == "filter":
            lines.append(f"- « {t.matched} » → filtre « {t.target} » : {t.definition}")
        elif t.kind == "column":
            lines.append(f"- « {t.matched} » → colonne {t.definition}{extra}")
        else:
            lines.append(f"- « {t.matched} » → {t.definition}")
    return "\n".join(lines)

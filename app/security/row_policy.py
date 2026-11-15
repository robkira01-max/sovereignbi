"""Sécurité par ligne (P-068), échec fermé.

Fichier de règles (`SOVEREIGN_ROW_POLICIES`, défaut `data/row_policies.yaml`) :

    policies:
      - {table: ventes, column: region, scope: region}

Une table « protégée » ne se lit qu'à travers un filtre : chaque référence à la table dans le SQL
devient `(SELECT * FROM t WHERE CAST(col AS VARCHAR) IN (valeurs du périmètre)) AS alias`.
La réécriture est faite dans `DataStore.execute`, seul passage vers DuckDB.

Qui voit quoi (quand au moins une règle existe) :
- compte web **admin** ou clé API **admin** : tout ;
- compte web non-admin : seulement les valeurs de son périmètre (`user_scopes`) ; **sans périmètre pour
  une règle = refus** (jamais « tout voir ») ;
- clé API viewer/editor, requête sans identité (planificateur, jeton d'intégration/partage, tâche de fond) :
  **refus** pour toute table protégée.
Aucune règle (fichier absent ou vide) = comportement inchangé.
"""
from __future__ import annotations

import os
import re
import threading
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path

import sqlglot
import yaml
from sqlglot import exp

_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
MAX_VALUES_PER_SCOPE = 200
MAX_VALUE_LEN = 200


class RowPolicyError(ValueError):
    """Fichier de règles invalide (message destiné à l'administrateur)."""


class AccessDenied(PermissionError):
    """Accès refusé par la sécurité par ligne."""


@dataclass(frozen=True)
class Policy:
    table: str
    column: str
    scope: str


@dataclass(frozen=True)
class Principal:
    kind: str                 # "admin" | "user" | "key"
    user_id: int | None = None


current_principal: ContextVar[Principal | None] = ContextVar("current_principal", default=None)


@contextmanager
def as_principal(p: Principal | None):
    tok = current_principal.set(p)
    try:
        yield
    finally:
        current_principal.reset(tok)


# ── règles ───────────────────────────────────────────────────────────────────

def _path() -> Path:
    return Path(os.environ.get("SOVEREIGN_ROW_POLICIES", "data/row_policies.yaml"))


_cache_lock = threading.Lock()
_cache: tuple[str, tuple[int, int], list[Policy]] | None = None


def load_policies() -> list[Policy]:
    """Règles du fichier (mises en cache selon la date de modification). Fichier illisible : RowPolicyError."""
    global _cache
    p = _path()
    if not p.exists():
        if os.environ.get("SOVEREIGN_ROW_POLICIES"):     # chemin demandé explicitement mais absent : jamais « pas de protection »
            raise RowPolicyError("SOVEREIGN_ROW_POLICIES est défini mais le fichier est introuvable.")
        return []
    st = p.stat()
    sig = (st.st_mtime_ns, st.st_size)
    with _cache_lock:
        if _cache and _cache[0] == str(p) and _cache[1] == sig:
            return _cache[2]
    try:
        raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict) or set(raw) - {"policies"}:
            raise RowPolicyError("Le fichier doit contenir uniquement la clé « policies » (faute de frappe ?).")
        if "policies" not in raw:
            raise RowPolicyError("Clé « policies » absente : un fichier vide ne protège rien.")
        items = raw["policies"]
        if not isinstance(items, list):
            raise RowPolicyError("« policies » doit être une liste.")
        out: list[Policy] = []
        for i, d in enumerate(items, 1):
            if not isinstance(d, dict) or not {"table", "column", "scope"} <= set(d):
                raise RowPolicyError(f"Règle {i} : champs attendus table, column, scope.")
            for k in ("table", "column", "scope"):
                if not isinstance(d[k], str) or not _IDENT_RE.match(d[k]):
                    raise RowPolicyError(f"Règle {i} : « {k} » doit être un identifiant simple (lettres, chiffres, _).")
            out.append(Policy(d["table"].lower(), d["column"], d["scope"]))
        keys = [(x.table, x.scope) for x in out]
        if len(set(keys)) != len(keys):
            raise RowPolicyError("Règle en double (même table et même périmètre).")
    except RowPolicyError:
        raise
    except Exception as e:  # noqa: BLE001 - toute anomalie du fichier est une erreur de règles, jamais une 500 opaque
        raise RowPolicyError(f"Fichier de règles illisible : {type(e).__name__}") from None
    with _cache_lock:
        _cache = (str(p), sig, out)
    return out


def active() -> bool:
    """Vrai si au moins une règle existe. Un fichier invalide compte comme actif (échec fermé)."""
    try:
        return bool(load_policies())
    except RowPolicyError:
        return True


# ── périmètres des utilisateurs (table dans la base d'authentification) ─────

def _conn():
    from app.auth import security as sec
    c = sec._conn()
    c.execute("CREATE TABLE IF NOT EXISTS user_scopes ("
              "user_id INTEGER NOT NULL, scope TEXT NOT NULL, value TEXT NOT NULL, "
              "PRIMARY KEY (user_id, scope, value))")
    return c


def get_scopes(user_id: int) -> dict[str, list[str]]:
    from contextlib import closing
    with closing(_conn()) as c:
        rows = c.execute("SELECT scope, value FROM user_scopes WHERE user_id=? ORDER BY scope, value", (user_id,)).fetchall()
    out: dict[str, list[str]] = {}
    for r in rows:
        out.setdefault(r["scope"], []).append(r["value"])
    return out


def set_scope(user_id: int, scope: str, values: list[str]) -> int:
    from contextlib import closing
    declared = {p.scope for p in load_policies()}
    if scope not in declared:
        raise RowPolicyError(f"Périmètre inconnu : « {scope} » (déclarés : {', '.join(sorted(declared)) or 'aucun'}).")
    clean = sorted({v.strip() for v in values if v.strip()})
    if len(clean) > MAX_VALUES_PER_SCOPE or any(len(v) > MAX_VALUE_LEN for v in clean):
        raise RowPolicyError(f"Au plus {MAX_VALUES_PER_SCOPE} valeurs de {MAX_VALUE_LEN} caractères.")
    with closing(_conn()) as c, c:
        c.execute("DELETE FROM user_scopes WHERE user_id=? AND scope=?", (user_id, scope))
        c.executemany("INSERT INTO user_scopes (user_id, scope, value) VALUES (?,?,?)", [(user_id, scope, v) for v in clean])
    return len(clean)


def delete_user_scopes(user_id: int) -> int:
    from contextlib import closing
    with closing(_conn()) as c, c:
        return c.execute("DELETE FROM user_scopes WHERE user_id=?", (user_id,)).rowcount


def check_can_replace(table: str) -> None:
    """Un compte non-admin ne remplace pas une table protégée (intégrité). Sans identité (démarrage, CLI) : permis."""
    who = current_principal.get()
    if who is not None and who.kind != "admin" and any(p.table == table.lower() for p in load_policies()):
        raise AccessDenied(f"La table « {table} » est protégée : seul un administrateur peut la remplacer.")


# ── réécriture ───────────────────────────────────────────────────────────────

def apply(sql: str) -> str:
    """SQL → SQL filtré pour le principal courant. Lève AccessDenied. Inchangé si aucune règle."""
    policies = load_policies()        # RowPolicyError remonte : un fichier cassé n'ouvre jamais l'accès
    if not policies:
        return sql
    by_table: dict[str, list[Policy]] = {}
    for p in policies:
        by_table.setdefault(p.table, []).append(p)
    try:
        tree = sqlglot.parse_one(sql, read="duckdb")
    except sqlglot.errors.SqlglotError:
        raise AccessDenied("Requête illisible : refusée (sécurité par ligne active).") from None
    ctes = {c.alias.lower() for c in tree.find_all(exp.CTE)}
    tables = [t for t in tree.find_all(exp.Table) if t.name]
    if any(not t.name for t in tree.find_all(exp.Table)):
        raise AccessDenied("Source de données non nommée (fonction de table ?) : refusée (sécurité par ligne active).")
    protected = [t for t in tables if t.name.lower() in by_table]
    if any(c in by_table for c in ctes):
        raise AccessDenied("Un alias de requête reprend le nom d'une table protégée : refusé.")
    if not protected:
        return sql
    if not isinstance(tree, (exp.Select, exp.Union, exp.Subquery)):
        raise AccessDenied("Seules les requêtes de lecture sont permises sur une table protégée.")

    who = current_principal.get()
    if who is not None and who.kind == "admin":
        return sql
    if who is None or who.kind != "user" or who.user_id is None:
        raise AccessDenied("Accès refusé : cette table est protégée et la requête n'a pas d'identité autorisée.")
    scopes = get_scopes(who.user_id)

    for t in protected:
        conds = []
        for pol in by_table[t.name.lower()]:
            vals = scopes.get(pol.scope)
            if not vals:
                raise AccessDenied(f"Accès refusé : aucun périmètre « {pol.scope} » n'est défini pour votre compte.")
            conds.append(exp.In(
                this=exp.Cast(this=exp.column(pol.column, quoted=True), to=exp.DataType.build("VARCHAR")),
                expressions=[exp.Literal.string(v) for v in vals]))
        where = conds[0] if len(conds) == 1 else exp.and_(*conds)
        inner = exp.select("*").from_(exp.Table(this=exp.to_identifier(t.name, quoted=True))).where(where)
        alias = t.alias or t.name
        t.replace(inner.subquery(alias))
    return tree.sql(dialect="duckdb")

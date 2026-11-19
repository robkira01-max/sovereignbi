"""Sources de confiance du « Calculé » et protection des tables sources (P-080, MOYEN-1).

Une réponse « Calculé » du chat ne lit que des tables dont le contenu n'a pas pu être déposé par un utilisateur :
  - le pack Audit (préfixe `audit_`, jamais créé par un upload : `DataStore.load_dataframe` le refuse) ;
  - ou un jeu de données certifié, dont l'empreinte de contenu correspond encore à la certification (P-069).
Une table référencée par `formula_inputs` ne peut pas être remplacée, quel que soit le rôle : un changement de
données passe par un nouvel import versionné (P-074), qui produit une nouvelle empreinte.
"""
from __future__ import annotations

from collections.abc import Callable

from app.data.duckdb_store import AUDIT_NAMESPACE, RESERVED_TABLES

_provider: Callable[[], object | list | None] | None = None


class ProtectedTable(ValueError):
    pass


def set_model_provider(fn: Callable[[], object | list | None] | None) -> None:
    """Fournit le(s) modèle(s) sémantique(s) à protéger (posé par app.main) sans que ce module dépende de l'application.
    Le fournisseur renvoie un modèle ou une liste de modèles (modèle par défaut + tous les secteurs)."""
    global _provider
    _provider = fn


def protected_tables(model) -> set[str]:
    out: set[str] = set()
    for m in getattr(model, "metrics", []) or []:
        for b in (m.formula_inputs or {}).values():
            if b.get("table"):
                out.add(b["table"].lower())
    return out


def check_can_replace(table: str) -> None:
    """Lève `ProtectedTableError` si `table` sert de source à une mesure calculée. Échec FERMÉ : modèle illisible → refus."""
    from app.data.duckdb_store import ProtectedTableError
    from app.security.actor import audit_soft
    if _provider is None:
        return
    try:
        got = _provider()
        models = got if isinstance(got, list) else [got]
        protected = set().union(*(protected_tables(m) for m in models if m is not None)) if models else set()
    except Exception:
        audit_soft("table_replace_refused", table=table, reason="model_unreadable")
        raise ProtectedTableError("Remplacement refusé : la configuration des mesures calculées est illisible. Corrigez-la d'abord.") from None
    if table.lower() in protected:
        audit_soft("table_replace_refused", table=table, reason="formula_source")
        raise ProtectedTableError(
            f"La table « {table} » est une source de calcul certifié : elle ne peut pas être remplacée. "
            "Passez par un nouvel import versionné du pack Audit.")


def is_audit_namespace(table: str) -> bool:
    """Contrôle STATIQUE de nom (validation de configuration). `audit_financial_records` est alimentée par des imports
    d'utilisateurs : elle n'est jamais de confiance d'office (il faut une certification à jour)."""
    t = table.lower()
    return t.startswith(AUDIT_NAMESPACE) and t not in RESERVED_TABLES and t != "audit_financial_records"


def untrusted_reason(store, table: str) -> str | None:
    """None si la table est une source acceptable pour un chiffre « Calculé », sinon la raison du refus.
    De confiance : table de référence créée par le code du produit pendant CE démarrage, ou jeu certifié à jour."""
    if table.lower() in {t.lower() for t in getattr(store, "trusted", set())}:
        return None
    from app.certification.registry import status
    st = status(store, table).get("status")
    if st == "certified":
        return None
    return f"la table « {table} » n'est ni une table du pack Audit ni un jeu certifié à jour (statut : {st})"

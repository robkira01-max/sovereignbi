"""Mode strict de l'IA (SOVEREIGN_AI_STRICT) : aucune donnée des tables du client n'est envoyée au modèle.

Ce que le mode strict retire des prompts :
- les lignes d'exemple de chaque table (le schéma — noms et types de colonnes — reste envoyé) ;
- les lignes de résultat servant à rédiger la réponse (la réponse est alors rédigée localement, sans IA) ;
- les extraits de documents importés ;
- les insights IA de tuiles (désactivés) ;
- les réponses précédentes de l'historique du chat (seules les questions de l'utilisateur sont renvoyées) ;
- les valeurs citées dans les messages d'erreur renvoyés au modèle pour corriger une requête.

Ce qui part encore : la question de l'utilisateur, les noms de tables et de colonnes, le modèle sémantique
(mesures, filtres, synonymes écrits par l'administrateur), les questions/SQL des exemples d'apprentissage.
Le mode strict réduit la fuite ; il ne remplace pas un modèle local.

Activation (SOVEREIGN_AI_STRICT) :
- `1`/`true`/`yes`/`on` : actif ; `0`/`false`/`no`/`off` : désactivé explicitement ;
- vide, absent ou valeur non reconnue : **automatique** — actif dès que LLM_PROVIDER n'est pas `ollama` (fournisseur
  externe, y compris une valeur mal orthographiée : dans le doute, on protège), inactif avec le modèle local.
Désactiver explicitement le mode avec un fournisseur externe est possible mais signalé au démarrage.
"""
from __future__ import annotations

import os
import re

_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off"}


def external_provider() -> bool:
    """Vrai si le LLM n'est pas le modèle local (tout ce qui n'est pas « ollama », fautes de frappe comprises)."""
    return os.environ.get("LLM_PROVIDER", "ollama").strip().lower() != "ollama"


def explicitly_disabled() -> bool:
    return os.environ.get("SOVEREIGN_AI_STRICT", "").strip().lower() in _FALSE


def strict() -> bool:
    v = os.environ.get("SOVEREIGN_AI_STRICT", "").strip().lower()
    if v in _TRUE:
        return True
    if v in _FALSE:
        return False
    return external_provider()            # automatique : actif avec un fournisseur externe


_QUOTED = re.compile(r"'[^']*'|\"[^\"]*\"")


def redact_error(message: str, limit: int = 240) -> str:
    """Retire les valeurs citées (« Could not convert string 'abc' ») d'un message d'erreur de base de données."""
    return _QUOTED.sub("'<valeur>'", message)[:limit]


def local_answer(columns: list[str], rows: list) -> str:
    """Réponse rédigée sans IA à partir du résultat (le résultat est montré à l'utilisateur, pas envoyé au modèle)."""
    if not rows:
        return "Aucun résultat pour cette question."
    if len(rows) == 1 and len(columns) == 1:
        return f"{columns[0]} : {rows[0][0]}"
    cols = ", ".join(columns[:6]) + ("…" if len(columns) > 6 else "")
    plural = "s" if len(rows) > 1 else ""
    return f"{len(rows)} ligne{plural} (colonnes : {cols}). Consultez le tableau ci-dessous."


def describe() -> str:
    return ("Mode strict actif : aucune ligne de données, aucun extrait de document ni aucun résultat n'est transmis au modèle "
            "(seuls la question, les noms de tables et de colonnes et le modèle sémantique le sont).")

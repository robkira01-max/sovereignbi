"""Client DeepSeek pour tâches de développement uniquement.

RÈGLES STRICTES (voir PLAN.md § Politique DeepSeek) :
- Autorisé : paires question/SQL sur schémas synthétiques, revue de code,
  brouillons de tests, docstrings, traductions.
- INTERDIT : toute donnée/schéma client, secrets, clés, configuration déploiement.
- Ce module n'est JAMAIS importé par app/. Un test CI vérifie ce point.
"""
import os

import httpx

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "")  # consulter la doc officielle au moment de l'usage
_BASE_URL = "https://api.deepseek.com"


def complete(system: str, user: str, model: str | None = None) -> str:
    """Appelle l'API DeepSeek. Données synthétiques uniquement."""
    if not DEEPSEEK_API_KEY:
        raise EnvironmentError("DEEPSEEK_API_KEY non définie.")
    m = model or DEEPSEEK_MODEL
    if not m:
        raise EnvironmentError("DEEPSEEK_MODEL non défini. Consulter la doc officielle pour le nom du modèle.")
    r = httpx.post(
        f"{_BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"},
        json={
            "model": m,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0,
        },
        timeout=120.0,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

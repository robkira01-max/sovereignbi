"""Tables de référence SYNTHÉTIQUES du pack Audit (P-080) : cas de test des formules, jamais des données réelles.

Elles sont créées par le code du produit dans l'espace `audit_` (qu'aucun upload ne peut créer ni remplacer), ce qui
en fait des sources acceptables pour un chiffre « Calculé ». Activées par `SOVEREIGN_AUDIT_REFERENCE_DIR`.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_reference_tables(store, directory: str | Path) -> list[str]:
    d = Path(directory)
    if not d.is_dir():
        return []
    loaded = []
    for f in sorted(d.glob("audit_*.csv")):
        loaded.append(store.load_trusted_table(f.stem, pd.read_csv(f)))
    return loaded

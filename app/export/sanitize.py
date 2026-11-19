"""Neutralisation des formules à l'export (P-082, injection CSV/Excel).

Une cellule TEXTE qui commence par `=`, `+`, `-`, `@`, tabulation ou retour chariot peut être exécutée comme
formule à l'ouverture dans Excel ou LibreOffice. Cette fonction unique préfixe d'une apostrophe toute cellule
texte dangereuse ; elle est appelée par TOUT export tabulaire (Excel, CSV de tuile, SDMX-CSV…).

Règles :
- seules les valeurs de type `str` sont modifiées : les nombres réels (int, float, Decimal), booléens, dates et
  None restent intacts (un montant exporté reste un nombre exploitable) ;
- la neutralisation se fait à la SORTIE uniquement : la donnée importée n'est jamais modifiée ;
- limite connue : un texte comme « -5 » stocké comme chaîne apparaîtra avec une apostrophe, par prudence.
Un test d'inventaire (`tests/test_export_sanitize.py`) échoue si un module qui écrit un CSV ou un classeur Excel
n'importe pas ce module.
"""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

TRIGGERS = ("=", "+", "-", "@", "\t", "\r", "\n")


def neutralize_cell(value: Any) -> Any:
    """Préfixe d'une apostrophe une cellule texte qui commence par un caractère déclencheur."""
    if isinstance(value, str) and value[:1] in TRIGGERS:
        return "'" + value
    return value


def neutralize_row(row: Iterable[Any]) -> list[Any]:
    return [neutralize_cell(v) for v in row]

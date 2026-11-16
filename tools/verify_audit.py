#!/usr/bin/env python3
"""Vérifie la chaîne d'intégrité du journal d'audit (P-071), sans démarrer l'application.

Usage : python tools/verify_audit.py [chemin] [--anchor-entries N --anchor-hash HEX]
Code de sortie : 0 = chaîne intacte (et ancrage conforme s'il est fourni), 1 = altération détectée, 2 = usage.
Limites : voir app/feedback.py::verify_audit_chain (suppression de la fin non détectée sans ancrage ; chaîne non signée).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.feedback import AUDIT_PATH, verify_audit_chain  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", nargs="?", type=Path, default=AUDIT_PATH)
    ap.add_argument("--anchor-entries", type=int)
    ap.add_argument("--anchor-hash")
    a = ap.parse_args(argv)
    if (a.anchor_entries or 0) > 0 and not a.anchor_hash or (a.anchor_hash and not a.anchor_entries):
        print("--anchor-entries (> 0) et --anchor-hash vont ensemble.", file=sys.stderr)
        return 2
    r = verify_audit_chain(a.path, a.anchor_entries, a.anchor_hash)
    print(f"entrées : {r.entries}\nhead    : {r.head or '(vide)'}")
    if r.anchor_checked:
        print(f"ancrage : {'conforme' if r.anchor_ok else 'NON CONFORME'}")
    if r.first_break:
        print(f"ALTÉRATION à la ligne {r.first_break['line']} : {r.first_break['reason']}")
    print("Chaîne intacte." if r.valid else "Chaîne NON valide.")
    print("Notez `entrées` et `head` hors du serveur : ils servent d'ancrage pour détecter une troncature.")
    return 0 if r.valid else 1


if __name__ == "__main__":
    sys.exit(main())

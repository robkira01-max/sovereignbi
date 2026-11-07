#!/usr/bin/env python3
"""Téléchargement des données UN Comtrade Plus pour Djibouti (reporter 262).

Usage:
    python tools/ingest_comtrade.py                      # exports 2023 (top 15)
    python tools/ingest_comtrade.py --year 2022 --flow M # imports 2022
    python tools/ingest_comtrade.py --dry-run            # test sans appel API

Prérequis:
    COMTRADE_API_KEY=... dans .env ou dans l'environnement.

Licence des données : UN Statistics Division — usage institutionnel.
Voir https://comtradeplus.un.org/Legal/Terms avant toute publication.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Allow running from project root without installing the package
sys.path.insert(0, str(Path(__file__).parent.parent))


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingestion Comtrade Plus — Djibouti")
    parser.add_argument("--year", type=int, default=2023, help="Année (défaut 2023)")
    parser.add_argument("--flow", choices=["X", "M"], default="X",
                        help="X=exports, M=imports (défaut X)")
    parser.add_argument("--reporter", type=int, default=262,
                        help="Code Comtrade du pays reporter (défaut 262=Djibouti)")
    parser.add_argument("--max-records", type=int, default=15,
                        help="Nombre max de partenaires (défaut 15)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Vérifie la clé et affiche la config sans appeler l'API")
    args = parser.parse_args()

    # Load .env if present
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

    api_key = os.environ.get("COMTRADE_API_KEY", "").strip()
    if not api_key:
        print("ERREUR : COMTRADE_API_KEY non définie dans .env ou l'environnement.", file=sys.stderr)
        print("Obtenez une clé gratuite sur https://comtradeplus.un.org", file=sys.stderr)
        sys.exit(1)

    print(f"Config : reporter={args.reporter}, year={args.year}, flow={args.flow}, "
          f"max={args.max_records}, dry_run={args.dry_run}")
    print(f"Clé : {api_key[:6]}{'*' * max(0, len(api_key) - 6)}")

    if args.dry_run:
        print("--dry-run : aucun appel API effectué.")
        return

    from app.data.comtrade_client import ComtradeClient
    client = ComtradeClient(api_key=api_key)
    print("Appel API Comtrade Plus…")
    flows = client.get_trade_flows(
        reporter_code=args.reporter,
        year=args.year,
        flow_code=args.flow,
        max_records=args.max_records,
    )

    if not flows:
        print("Aucun flux retourné (vérifiez l'année et les paramètres).")
        return

    print(f"\n{len(flows)} flux retournés :")
    for f in flows:
        print(f"  {f.destination:20s}  {f.flow_code}  {f.trade_value_usd:>14,.0f} USD  "
              f"(tonnage_k={f.tonnage_k})")

    # Optionally save to data/comtrade_cache.json
    out = Path(__file__).parent.parent / "data" / "comtrade_cache.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    cache = {
        "reporter": args.reporter,
        "year": args.year,
        "flow": args.flow,
        "flows": [
            {
                "id": f.id, "from_lng": f.from_lng, "from_lat": f.from_lat,
                "to_lng": f.to_lng, "to_lat": f.to_lat,
                "commodity": f.commodity, "tonnage_k": f.tonnage_k,
                "color": f.color, "destination": f.destination,
                "country": f.country, "trade_value_usd": f.trade_value_usd,
                "flow_code": f.flow_code, "year": f.year,
            }
            for f in flows
        ],
    }
    out.write_text(json.dumps(cache, ensure_ascii=False, indent=2))
    print(f"\nCache sauvegardé : {out}")


if __name__ == "__main__":
    main()

"""CLI d'ingestion NISR — National Institute of Statistics of Rwanda.

Usage:
    python tools/ingest_nisr.py --search "population"
    python tools/ingest_nisr.py --id <dataset_id> [--table <name>] [--dry-run]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.data.nisr_client import NISRClient


def cmd_search(q: str, rows: int) -> None:
    client = NISRClient()
    print(f"🔍 Recherche NISR (Rwanda) : {q!r}\n")
    datasets = client.search_datasets(q, rows=rows)
    if not datasets:
        print("Aucun résultat.")
        return
    for d in datasets:
        perm = "✅" if d.is_permitted else "❌"
        print(f"  {perm} [{d.id[:8]}…] {d.title}")
        print(f"     Licence : {d.license_id} · Ressources : {len(d.resources)}")


def cmd_fetch(dataset_id: str, table_name: str | None, max_rows: int, dry_run: bool) -> None:
    client = NISRClient()
    print(f"📥 Dataset NISR : {dataset_id!r}\n")

    ds = client.get_dataset(dataset_id)
    print(f"  Titre   : {ds.title}")
    print(f"  Licence : {ds.license_id} — {ds.license_reason}")

    if not ds.is_permitted:
        print("❌ Ingestion refusée (licence non autorisée).")
        sys.exit(1)

    csv_resources = [
        r for r in ds.resources
        if r.get("format", "").upper() in ("CSV", "TEXT/CSV")
        and r.get("url", "").startswith("https://")
    ]
    if not csv_resources:
        print("❌ Aucune ressource CSV disponible.")
        sys.exit(1)

    url = csv_resources[0]["url"]
    print(f"  URL CSV : {url}")

    if dry_run:
        print("\nDry-run — aucun téléchargement effectué.")
        return

    df = client.fetch_csv(url, max_rows=max_rows)
    tname = table_name or ds.name.replace("-", "_")[:64]
    print(f"\n✅ {len(df)} lignes · {len(df.columns)} colonnes → table '{tname}'")
    print(f"   Colonnes : {', '.join(df.columns[:8])}{'…' if len(df.columns) > 8 else ''}")
    print("\n   Pour charger dans DuckDB, utilisez POST /connectors/nisr via l'API.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--search", metavar="QUERY")
    group.add_argument("--id", metavar="DATASET_ID")
    parser.add_argument("--table", metavar="NAME")
    parser.add_argument("--rows", type=int, default=20)
    parser.add_argument("--max-rows", type=int, default=50_000, dest="max_rows")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.search:
        cmd_search(args.search, rows=args.rows)
    else:
        cmd_fetch(args.id, args.table, args.max_rows, args.dry_run)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Charge les jeux de données INSTAD dans un DuckDB persistant pour les démos pilote.

Usage:
  .venv/bin/python tools/load_instad_datasets.py [--db PATH] [--verify]

Options:
  --db PATH   Chemin du fichier DuckDB cible (défaut: data/instad/instad_pilot.duckdb)
  --verify    Affiche un résumé des tables chargées après l'import
  --dry-run   Valide les CSV sans écrire dans DuckDB

Données :
  data/instad/population_region.csv  — RGPH 2009/2016/2024, 6 régions
  data/instad/education_region.csv   — Scolarisation et alphabétisation
  data/instad/emploi_region.csv      — Marché du travail
  data/instad/logement.csv           — Conditions de logement et accès aux services
  data/instad/pib_secteurs.csv       — Décomposition sectorielle du PIB 2018-2024
  data/instad/commerce_exterieur.csv — Flux commerciaux par partenaire 2018-2024
  data/instad/indicateurs_macro.csv  — Indicateurs macroéconomiques 2018-2024

Note : données fictives d'illustration — à remplacer par les fichiers officiels
INSTAD (https://www.instad.dj) lors du déploiement pilote.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "instad"
DEFAULT_DB = DATA_DIR / "instad_pilot.duckdb"

DATASETS: list[tuple[str, str]] = [
    ("population_region.csv", "population_region"),
    ("education_region.csv", "education_region"),
    ("emploi_region.csv", "emploi_region"),
    ("logement.csv", "logement"),
    ("pib_secteurs.csv", "pib_secteurs"),
    ("commerce_exterieur.csv", "commerce_exterieur"),
    ("indicateurs_macro.csv", "indicateurs_macro"),
]


def validate_csv(path: Path) -> tuple[int, list[str]]:
    import csv
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        rows = sum(1 for _ in reader)
    return rows, headers


def load_datasets(db_path: Path, *, dry_run: bool = False, verbose: bool = True) -> dict[str, int]:
    import pandas as pd

    counts: dict[str, int] = {}
    errors: list[str] = []

    for filename, table_name in DATASETS:
        csv_path = DATA_DIR / filename
        if not csv_path.exists():
            errors.append(f"MANQUANT : {csv_path}")
            continue

        row_count, headers = validate_csv(csv_path)
        if verbose:
            print(f"  {filename}: {row_count} lignes, {len(headers)} colonnes")

        if not dry_run:
            df = pd.read_csv(csv_path)
            counts[table_name] = len(df)

    if errors:
        for e in errors:
            print(f"  ERREUR: {e}", file=sys.stderr)
        if not dry_run:
            raise FileNotFoundError(f"{len(errors)} fichier(s) manquant(s)")

    if dry_run:
        print("  (dry-run — aucune écriture dans DuckDB)")
        return counts

    import duckdb
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
    try:
        for filename, table_name in DATASETS:
            csv_path = DATA_DIR / filename
            if not csv_path.exists():
                continue
            df = pd.read_csv(csv_path)
            con.register("_tmp", df)
            con.execute(f'CREATE OR REPLACE TABLE "{table_name}" AS SELECT * FROM _tmp')
            con.unregister("_tmp")
            counts[table_name] = len(df)
            if verbose:
                print(f"    → TABLE {table_name} chargée ({len(df)} lignes)")

        # Metadata table for audit trail
        import json
        from datetime import UTC, datetime
        meta = {
            "loaded_at": datetime.now(UTC).isoformat(),
            "source": "data/instad/ (données fictives — pilote INSTAD)",
            "tables": list(counts.keys()),
            "total_rows": sum(counts.values()),
        }
        con.execute(
            "CREATE OR REPLACE TABLE _meta AS "
            "SELECT ? AS loaded_at, ? AS source, ? AS tables_json",
            [meta["loaded_at"], meta["source"], json.dumps(meta["tables"])],
        )
    finally:
        con.close()

    return counts


def print_verify(db_path: Path) -> None:
    import duckdb
    con = duckdb.connect(str(db_path), read_only=True)
    print("\n=== Résumé des tables chargées ===")
    tables = con.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'main' AND table_name NOT LIKE '\\_%' ESCAPE '\\' "
        "ORDER BY table_name"
    ).fetchall()
    for (name,) in tables:
        count = con.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
        cols = con.execute(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_name = ?", [name]
        ).fetchone()[0]
        print(f"  {name:30s} {count:5d} lignes  {cols:2d} colonnes")
    con.close()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--db", default=str(DEFAULT_DB), help="Chemin du fichier DuckDB")
    p.add_argument("--verify", action="store_true", help="Vérifier après import")
    p.add_argument("--dry-run", action="store_true", help="Valider sans écrire")
    args = p.parse_args(argv)

    db_path = Path(args.db)
    dry = args.dry_run

    print(f"{'[DRY-RUN] ' if dry else ''}Chargement des datasets INSTAD…")
    print(f"  Source : {DATA_DIR}")
    print(f"  Cible  : {db_path if not dry else '(aucune)'}")
    print()

    try:
        counts = load_datasets(db_path, dry_run=dry)
    except FileNotFoundError as exc:
        print(f"\nEchec : {exc}", file=sys.stderr)
        return 1

    total = sum(counts.values()) if counts else 0
    print(f"\n{'Validation' if dry else 'Import'} terminé : "
          f"{len(DATASETS)} fichiers, {total} lignes au total.")

    if args.verify and not dry:
        print_verify(db_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())

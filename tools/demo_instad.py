#!/usr/bin/env python3
"""Démo pilote INSTAD — 10 questions types sur les données djiboutiennes.

Charge les CSV INSTAD dans un DuckDB en mémoire et répond aux questions
avec le pipeline SQL de SovereignBI.

Usage:
  .venv/bin/python tools/demo_instad.py
  .venv/bin/python tools/demo_instad.py --dry-run     # valide sans appeler le LLM
  .venv/bin/python tools/demo_instad.py --q 3         # question n°3 uniquement
  .venv/bin/python tools/demo_instad.py --list        # liste les questions
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "instad"

DEMO_QUESTIONS = [
    {
        "id": 1,
        "category": "Démographie",
        "question": "Quelle est la population totale de Djibouti selon le dernier recensement (2024) ?",
        "expected_tables": ["population_region"],
    },
    {
        "id": 2,
        "category": "Démographie",
        "question": "Quelles sont les trois régions les plus peuplées de Djibouti en 2024 ?",
        "expected_tables": ["population_region"],
    },
    {
        "id": 3,
        "category": "Emploi",
        "question": "Quel est le taux de chômage moyen à Djibouti, et quelle région est la plus touchée ?",
        "expected_tables": ["emploi_region"],
    },
    {
        "id": 4,
        "category": "Éducation",
        "question": "Comment a évolué le taux d'alphabétisation à Djibouti entre 2009 et 2024 ?",
        "expected_tables": ["education_region"],
    },
    {
        "id": 5,
        "category": "Logement",
        "question": "Quel pourcentage des ménages djiboutiens avait accès à l'électricité en 2024 ?",
        "expected_tables": ["logement"],
    },
    {
        "id": 6,
        "category": "Économie",
        "question": "Quel est le PIB de Djibouti en 2024 et son taux de croissance ?",
        "expected_tables": ["indicateurs_macro"],
    },
    {
        "id": 7,
        "category": "Économie",
        "question": "Quels sont les secteurs économiques qui contribuent le plus au PIB djiboutien ?",
        "expected_tables": ["pib_secteurs"],
    },
    {
        "id": 8,
        "category": "Commerce",
        "question": "Quels sont les principaux partenaires commerciaux de Djibouti à l'import et à l'export ?",
        "expected_tables": ["commerce_exterieur"],
    },
    {
        "id": 9,
        "category": "Commerce",
        "question": "Quelle est la balance commerciale de Djibouti en 2024 ?",
        "expected_tables": ["commerce_exterieur"],
    },
    {
        "id": 10,
        "category": "Multi-secteurs",
        "question": "Compare le taux d'urbanisation et le taux de chômage par région en 2024.",
        "expected_tables": ["population_region", "emploi_region"],
    },
]


def _load_store() -> object:
    """Load all INSTAD CSV files into a DataStore instance."""
    import pandas as pd

    sys.path.insert(0, str(PROJECT_ROOT))
    from app.data.duckdb_store import DataStore

    store = DataStore()
    csv_files = sorted(DATA_DIR.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(
            f"Aucun fichier CSV trouvé dans {DATA_DIR}. "
            "Exécutez d'abord : .venv/bin/python tools/load_instad_datasets.py --dry-run"
        )

    for csv_path in csv_files:
        df = pd.read_csv(csv_path)
        store.load_dataframe(csv_path.stem, df)
        print(f"  ✓ {csv_path.name} ({len(df)} lignes)")

    return store


def _run_sql_only(store, question: str) -> None:
    """Run a simple SQL demo without the LLM (for --dry-run)."""
    tables = sorted(store.tables)
    print(f"  Tables disponibles : {', '.join(tables)}")
    # Show a quick schema snippet
    schema = store.schema_description()
    print(f"  Schéma : {schema[:200]}…")


def _run_with_llm(store, question: str) -> None:
    """Run the full pipeline: SQL generation + LLM answer."""
    from app.llm import get_llm_client
    from app.pipeline.graph import build_graph, load_semantic

    llm = get_llm_client()
    sem = load_semantic()
    graph = build_graph(llm, store, sem)
    state = graph.invoke({"question": question, "dry_run": False})
    if state.get("error"):
        print(f"  ERREUR : {state['error']}")
    else:
        print(f"  SQL    : {state.get('sql', '?')}")
        print(f"  Lignes : {len(state.get('rows', []))}")
        print(f"  Réponse : {state.get('answer', '')}")


def run_demo(
    questions: list[dict],
    *,
    dry_run: bool = False,
    verbose: bool = True,
) -> int:
    print("=== Démo INSTAD — Dossier pilote Djibouti ===\n")
    print("Chargement des données…")

    try:
        store = _load_store()
    except FileNotFoundError as exc:
        print(f"\nEchec du chargement : {exc}", file=sys.stderr)
        return 1

    print(f"\n{len(store.tables)} tables chargées : {', '.join(sorted(store.tables))}\n")

    errors = 0
    for q in questions:
        print(f"[{q['id']:2d}] [{q['category']}] {q['question']}")
        try:
            if dry_run:
                _run_sql_only(store, q["question"])
                print("  (dry-run — LLM non appelé)\n")
            else:
                _run_with_llm(store, q["question"])
                print()
        except Exception as exc:  # noqa: BLE001
            print(f"  ERREUR : {exc}\n")
            errors += 1

    status = "avec des erreurs" if errors else "avec succès"
    print(f"\nDémo terminée {status} ({errors} erreur(s) sur {len(questions)} questions).")
    return 1 if errors else 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dry-run", action="store_true", help="Valide sans appeler le LLM")
    p.add_argument("--q", type=int, metavar="N", help="Exécute uniquement la question N")
    p.add_argument("--list", action="store_true", help="Affiche la liste des questions")
    args = p.parse_args(argv)

    if args.list:
        print("Questions disponibles :")
        for q in DEMO_QUESTIONS:
            print(f"  [{q['id']:2d}] [{q['category']:15s}] {q['question']}")
        return 0

    questions = DEMO_QUESTIONS
    if args.q is not None:
        questions = [q for q in DEMO_QUESTIONS if q["id"] == args.q]
        if not questions:
            print(f"Question {args.q} introuvable.", file=sys.stderr)
            return 1

    return run_demo(questions, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())

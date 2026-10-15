"""
Test pipeline SovereignBI avec données réelles Djibouti (HDX OCHA).
Usage : python tools/test_real_data.py [--ollama]
"""
import os, sys, time, argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ.setdefault("SOVEREIGN_EMBEDDER", "tfidf")

import pandas as pd
from app.data.duckdb_store import DataStore
from app.pipeline.graph import build_graph

DATA_DIR = Path(__file__).parent.parent / "data" / "real"

DATASETS = {
    "health_who":            DATA_DIR / "health_who.csv",
    "health_wb":             DATA_DIR / "health_wb.csv",
    "education":             DATA_DIR / "education.csv",
    "cerf_allocations":      DATA_DIR / "cerf_allocations.csv",
    "humanitarian_projects": DATA_DIR / "humanitarian_projects.csv",
    "funding":               DATA_DIR / "funding.csv",
    "food_security":         DATA_DIR / "food_security.csv",
}

QUESTIONS = [
    "Quelle est la dernière valeur disponible pour l'espérance de vie à Djibouti ?",
    "Quels projets humanitaires sont actifs à Djibouti et quel est leur budget total ?",
    "Quelle agence a reçu le plus de financement CERF pour Djibouti ?",
    "Quel est le taux d'inscription scolaire le plus récent à Djibouti ?",
    "Quel est le coût d'une alimentation saine à Djibouti selon les données FAO ?",
]


def load_store() -> DataStore:
    store = DataStore()
    for name, path in DATASETS.items():
        if not path.exists():
            print(f"  [SKIP] {name} — fichier absent")
            continue
        df = pd.read_csv(path)
        loaded = store.load_dataframe(name, df)
        count = store.con.execute(f'SELECT COUNT(*) FROM "{loaded}"').fetchone()[0]
        print(f"  [OK] {loaded:30s} {count:6d} lignes")
    return store


def run_tests(store: DataStore, llm, dry_run: bool = False):
    graph = build_graph(llm, store)
    results = []
    for i, q in enumerate(QUESTIONS, 1):
        print(f"\n[{i}/{len(QUESTIONS)}] {q}")
        t0 = time.time()
        state = graph.invoke({"question": q, "dry_run": dry_run})
        elapsed = time.time() - t0
        sql = state.get("sql", "—")
        answer = state.get("answer", "—")
        error = state.get("error")
        print(f"  SQL    : {sql[:120]}{'...' if len(sql) > 120 else ''}")
        if error:
            print(f"  ERREUR : {error}")
        print(f"  Réponse: {answer[:200]}")
        print(f"  Temps  : {elapsed:.1f}s")
        results.append({"question": q, "sql": sql, "answer": answer, "ok": not error, "ms": round(elapsed * 1000)})
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ollama", action="store_true", help="Utiliser Ollama (LLM réel)")
    parser.add_argument("--dry-run", action="store_true", help="Générer SQL uniquement, sans LLM answer")
    args = parser.parse_args()

    print("=== Chargement données réelles Djibouti ===")
    store = load_store()
    print(f"\nTables disponibles : {sorted(store.tables)}")

    print("\n=== Schéma ===")
    print(store.schema_description()[:2000])

    if args.ollama:
        from app.llm.ollama_client import OllamaClient
        llm = OllamaClient()
        print("\n=== Requêtes avec Ollama ===")
    else:
        # Mock LLM: returns a plausible SQL for each question
        class MockLLM:
            _sqls = [
                "SELECT gho_display, numeric, year_display FROM health_who WHERE country_code = 'DJI' AND LOWER(gho_display) LIKE '%life expect%' ORDER BY year_display DESC LIMIT 5",
                "SELECT name, currentrequestedfunds, startdate, enddate FROM humanitarian_projects ORDER BY currentrequestedfunds DESC LIMIT 10",
                "SELECT agencyname, SUM(totalamountapproved) AS total FROM cerf_allocations WHERE countrycode = 'DJI' GROUP BY agencyname ORDER BY total DESC LIMIT 5",
                "SELECT indicator_name, value, year FROM education WHERE country_iso3 = 'DJI' ORDER BY year DESC LIMIT 10",
                "SELECT item, element, value, unit, year FROM food_security WHERE iso3 = 'DJI' AND LOWER(item) LIKE '%healthy diet%' ORDER BY year DESC LIMIT 5",
            ]
            _idx = 0
            def complete(self, system, user):
                sql = self._sqls[self._idx % len(self._sqls)]
                self._idx += 1
                return f"```sql\n{sql}\n```"
        llm = MockLLM()
        print("\n=== Requêtes avec Mock LLM (SQL prédéfinis) ===")

    results = run_tests(store, llm, dry_run=args.dry_run)

    ok = sum(1 for r in results if r["ok"])
    print(f"\n=== Résumé : {ok}/{len(results)} requêtes réussies ===")
    for r in results:
        status = "✓" if r["ok"] else "✗"
        print(f"  {status} {r['ms']:5d}ms  {r['question'][:70]}")


if __name__ == "__main__":
    main()

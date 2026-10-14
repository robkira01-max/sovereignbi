#!/usr/bin/env python3
"""PremSQL-pattern benchmark runner for Sprint H3 sector questions.

Usage:
    python -m eval.run_benchmark_h3 [--lang fr] [--sector humanitarian] [--json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

BENCHMARK_FILE = Path(__file__).parent / "benchmark_h3.jsonl"


def load_questions(
    lang: str | None = None,
    sector: str | None = None,
) -> list[dict]:
    questions = []
    with BENCHMARK_FILE.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            q = json.loads(line)
            if lang and q.get("lang") != lang:
                continue
            if sector and q.get("sector") != sector:
                continue
            questions.append(q)
    return questions


def evaluate_sql(sql: str, item: dict) -> dict:
    """Check that the generated SQL contains expected keywords."""
    keywords = item.get("min_keywords", [])
    sql_upper = sql.upper()
    missing = [kw for kw in keywords if kw.upper() not in sql_upper]
    passed = len(missing) == 0
    return {
        "id": item["id"],
        "lang": item["lang"],
        "sector": item["sector"],
        "question": item["question"],
        "passed": passed,
        "missing_keywords": missing,
        "expected_table": item.get("expected_table"),
        "expected_metric": item.get("expected_metric"),
    }


def run_with_provider(provider_fn, questions: list[dict]) -> list[dict]:
    """Run benchmark using a callable provider(question: str, sector: str) -> sql: str."""
    results = []
    for item in questions:
        try:
            sql = provider_fn(item["question"], item["sector"])
        except Exception as exc:
            results.append(
                {
                    "id": item["id"],
                    "lang": item["lang"],
                    "sector": item["sector"],
                    "question": item["question"],
                    "passed": False,
                    "error": str(exc),
                }
            )
            continue
        results.append(evaluate_sql(sql, item))
    return results


def mock_provider(question: str, sector: str) -> str:
    """Trivial mock that returns a plausible SQL stub for testing."""
    sector_tables = {
        "humanitarian": "beneficiaires",
        "igad_economic": "indicateurs_economiques",
        "instad_census": "population_region",
    }
    table = sector_tables.get(sector, "data")
    q_lower = question.lower()

    # More specific patterns first, then generic aggregates
    if any(w in q_lower for w in ["kg", "quantité", "quantity", "cantidad", "كمية", "distribu"]):
        if any(w in q_lower for w in ["kg", "quantité", "quantity", "cantidad", "كمية"]):
            return "SELECT SUM(quantite_kg) FROM distributions"
        return "SELECT COUNT(DISTINCT id_distribution) FROM distributions"
    if any(w in q_lower for w in ["pdi", "idp", "déplacé", "displaced", "desplazado", "نازح"]):
        return "SELECT SUM(nb_personnes) FROM deplacements WHERE type_deplacement = 'interne'"
    if any(w in q_lower for w in ["croissance", "growth rate", "growth", "crecimiento", "نمو"]):
        return "SELECT AVG(taux_croissance_pib) FROM indicateurs_economiques"
    if any(w in q_lower for w in ["pib", "gdp", "producto"]):
        return "SELECT SUM(pib_usd) FROM indicateurs_economiques"
    if any(w in q_lower for w in ["ipc", "food security", "sécurité alimentaire"]):
        return "SELECT AVG(ipc_phase_moyenne) FROM securite_alimentaire"
    if any(w in q_lower for w in ["statut", "status", "répartis"]):
        return f"SELECT statut_protection, COUNT(*) FROM {table} GROUP BY statut_protection"
    if any(w in q_lower for w in ["origine", "origin", "origen"]):
        return "SELECT pays_origine, COUNT(*) FROM beneficiaires GROUP BY pays_origine LIMIT 5"
    if any(w in q_lower for w in ["site", "camp"]):
        return "SELECT site_camp, COUNT(*) FROM beneficiaires GROUP BY site_camp ORDER BY 2 DESC LIMIT 5"
    if any(w in q_lower for w in ["taux_chomage", "chômage", "unemployment", "desempleo"]):
        return "SELECT AVG(taux_chomage_pct) FROM emploi_region"
    if any(w in q_lower for w in ["population"]):
        return "SELECT SUM(population_totale) FROM population_region"
    if any(w in q_lower for w in ["total", "combien", "how many", "cuántos", "كم", "إجمالي"]):
        return f"SELECT SUM(nb_beneficiaires) FROM {table}"
    return f"SELECT * FROM {table} LIMIT 10"


def print_summary(results: list[dict], as_json: bool = False) -> None:
    total = len(results)
    passed = sum(1 for r in results if r.get("passed"))
    score = passed / total * 100 if total else 0

    if as_json:
        print(json.dumps({"total": total, "passed": passed, "score": score, "results": results}, ensure_ascii=False, indent=2))
        return

    print(f"\n{'='*60}")
    print(f"Sprint H3 Benchmark — {passed}/{total} passed ({score:.1f}%)")
    print(f"{'='*60}")
    for r in results:
        icon = "✓" if r.get("passed") else "✗"
        print(f"  {icon} [{r['lang'].upper()}/{r['sector'][:8]}] {r['question'][:60]}")
        if not r.get("passed"):
            missing = r.get("missing_keywords") or []
            err = r.get("error", "")
            if missing:
                print(f"      Missing: {missing}")
            if err:
                print(f"      Error: {err}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Sprint H3 benchmark runner")
    parser.add_argument("--lang", help="Filter by language (fr, en, es, ar)")
    parser.add_argument("--sector", help="Filter by sector ID")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--list", action="store_true", help="List questions and exit")
    args = parser.parse_args()

    questions = load_questions(lang=args.lang, sector=args.sector)

    if args.list:
        for q in questions:
            print(f"[{q['id']}] ({q['lang']}/{q['sector']}) {q['question']}")
        return

    if not questions:
        print("No questions match the filters.", file=sys.stderr)
        sys.exit(1)

    results = run_with_provider(mock_provider, questions)
    print_summary(results, as_json=args.json)
    failed = sum(1 for r in results if not r.get("passed"))
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()

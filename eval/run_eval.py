"""Harnais d'évaluation : execution accuracy (le résultat du SQL généré == celui du SQL de référence).

Usage : python -m eval.run_eval   (Ollama doit tourner ; OLLAMA_URL / LLM_MODEL configurables)
"""
import json
import sys
from pathlib import Path

import pandas as pd

from app.data.duckdb_store import DataStore
from app.llm.ollama_client import LLM, OllamaClient
from app.pipeline.graph import build_graph, load_semantic

HERE = Path(__file__).parent


def _norm(rows):
    return sorted(tuple(round(v, 4) if isinstance(v, float) else v for v in r) for r in rows)


def run_eval(llm: LLM, dataset: Path = HERE / "dataset.jsonl", data: Path = HERE / "ventes.csv") -> dict:
    store = DataStore()
    store.load_dataframe("ventes", pd.read_csv(data))
    graph = build_graph(llm, store, load_semantic())
    results = []
    for line in dataset.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        _, gold = store.execute(item["gold_sql"])
        s = graph.invoke({"question": item["question"]})
        ok = not s.get("error") and _norm(s.get("rows", [])) == _norm(gold)
        results.append({"question": item["question"], "ok": ok, "sql": s.get("sql"), "attempts": s.get("attempts")})
    score = sum(r["ok"] for r in results) / max(len(results), 1)
    return {"score": score, "n": len(results), "results": results}


if __name__ == "__main__":
    report = run_eval(OllamaClient())
    for r in report["results"]:
        print(("✅" if r["ok"] else "❌"), r["question"], "->", r["sql"])
    print(f"\nExecution accuracy : {report['score']:.0%} ({report['n']} questions)")
    sys.exit(0)

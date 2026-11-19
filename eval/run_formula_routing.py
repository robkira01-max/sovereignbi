"""Évaluation du routage chat → moteur de formules (P-080). Déterministe : aucun modèle de langage requis.

    .venv/bin/python -m eval.run_formula_routing [--json]

Mesure : la pastille attendue (calculé / exploratoire / calcul non effectué), la formule et la valeur, et qu'aucune
autre formule que celles attendues n'a été lancée (injection). Les résultats par modèle de génération (précision du
text-to-SQL sur les questions exploratoires) relèvent de P-078 : aucune précision n'est annoncée ici.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pandas as pd

from app import feedback
from app.data.duckdb_store import DataStore
from app.pipeline.formula_route import route_formula
from app.semantic.model import load_model

CASES = Path(__file__).with_name("formula_routing.jsonl")
MODEL = """
schema_version: "2"
tables:
  - name: audit_budget
    columns: [{name: realise, type: bigint}, {name: vote, type: bigint}, {name: encaisse, type: bigint}]
metrics:
  - name: "taux d'exécution budgétaire"
    aliases: ["exécution du budget"]
    sql: "SUM(realise) / SUM(vote)"
    tables: [audit_budget]
    formula: BUD001
    formula_inputs:
      depenses: {table: audit_budget, column: realise}
      budget_vote: {table: audit_budget, column: vote}
  - name: "taux de recouvrement"
    sql: "SUM(encaisse)"
    tables: [audit_budget]
    formula: REC001
  - name: "total voté"
    sql: "SUM(vote)"
    tables: [audit_budget]
"""


def evaluate() -> list[dict]:
    tmp = Path(tempfile.mkdtemp())
    feedback.AUDIT_PATH = tmp / "audit.jsonl"          # journal jetable : jamais le vrai journal
    (tmp / "m.yaml").write_text(MODEL, encoding="utf-8")
    model = load_model(tmp / "m.yaml")
    out = []
    for line in CASES.read_text(encoding="utf-8").splitlines():
        case = json.loads(line)
        store = DataStore()
        store.load_trusted_table("audit_budget", pd.DataFrame({"realise": pd.Series([114000000], dtype="int64"),
                                                     "vote": pd.Series([120000000], dtype="int64"),
                                                     "encaisse": pd.Series([5], dtype="int64")}))
        r = route_formula(model, case["question"], store, actor=f"api_key:{case['role']}", role=case["role"])
        got = "exploratory" if r is None else r["provenance"]
        names = [t[0] for t in store.con.execute("SHOW TABLES").fetchall()]
        runs = [r_[0] for r_ in store.con.execute("SELECT formula_code FROM audit_analysis_runs").fetchall()] if "audit_analysis_runs" in names else []
        ok = got == case["expect"]
        if ok and "formula" in case:
            ok = r["formula"]["code"] == case["formula"] and r["value"] == case["value"]
        if ok and "only_formulas" in case:
            ok = sorted(set(runs)) == sorted(case["only_formulas"])
        if ok and got != "calculated":
            ok = not runs and (r is None or r.get("value") is None)      # jamais de chiffre ni de run hors « calculé »
        out.append({"id": case["id"], "expect": case["expect"], "got": got, "ok": ok})
    return out


if __name__ == "__main__":
    results = evaluate()
    if "--json" in sys.argv:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for r in results:
            print(("OK  " if r["ok"] else "FAIL"), r["id"], "attendu", r["expect"], "obtenu", r["got"])
        print(f"{sum(r['ok'] for r in results)}/{len(results)} cas conformes")
    sys.exit(0 if all(r["ok"] for r in results) else 1)

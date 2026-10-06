from pathlib import Path

import pandas as pd

from app.data.duckdb_store import DataStore
from app.pipeline.graph import build_graph
from eval.run_eval import run_eval

HERE = Path(__file__).parent.parent / "eval"


class FakeLLM:
    """Répond de façon scriptée : 1re requête fausse, puis correction, puis résumé."""

    def __init__(self, sqls):
        self.sqls = list(sqls)
        self.calls = 0

    def complete(self, system, user):
        if "expert SQL" in system:
            self.calls += 1
            return f"```sql\n{self.sqls.pop(0)}\n```"
        return "Le chiffre d'affaires total est de 2550."


def make_store():
    s = DataStore()
    s.load_dataframe("ventes", pd.read_csv(HERE / "ventes.csv"))
    return s


def test_end_to_end():
    store = make_store()
    g = build_graph(FakeLLM(["SELECT SUM(montant) FROM ventes"]), store)
    out = g.invoke({"question": "CA total ?"})
    assert out["rows"][0][0] == 2550.0
    assert "2550" in out["answer"]


def test_retry_after_error():
    store = make_store()
    llm = FakeLLM(["SELECT SUM(montants) FROM ventes", "SELECT SUM(montant) FROM ventes"])
    out = build_graph(llm, store).invoke({"question": "CA total ?"})
    assert llm.calls == 2 and out["rows"][0][0] == 2550.0


def test_dangerous_sql_blocked_after_retries():
    store = make_store()
    llm = FakeLLM(["DROP TABLE ventes"] * 3)
    out = build_graph(llm, store).invoke({"question": "supprime tout"})
    assert out["error"] and "ventes" in store.tables
    assert out["attempts"] == 3


def test_dry_run_does_not_execute():
    store = make_store()
    out = build_graph(FakeLLM(["SELECT * FROM ventes"]), store).invoke({"question": "?", "dry_run": True})
    assert out["rows"] == [] and "LIMIT" in out["sql"].upper()


def test_eval_harness_scores_perfect_with_gold_llm():
    import json
    gold = [json.loads(l)["gold_sql"] for l in (HERE / "dataset.jsonl").read_text().splitlines() if l.strip()]
    report = run_eval(FakeLLM(gold))
    assert report["score"] == 1.0

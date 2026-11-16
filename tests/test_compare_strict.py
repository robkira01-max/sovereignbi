"""Outil de mesure appariée strict / ouvert (eval/compare_strict.py)."""
from __future__ import annotations

import json
import math
import os
from pathlib import Path

import pytest

os.environ.setdefault("SOVEREIGN_EMBEDDER", "tfidf")

from eval.compare_strict import (  # noqa: E402
    SqlOnly, load_items, mcnemar_exact, render_report, run_compare, summarize, wilson,
)

DATA = Path(__file__).resolve().parent.parent / "eval"
SMALL = DATA / "dataset.jsonl"


# ── statistiques ────────────────────────────────────────────────────────────

def test_mcnemar_exact_known_values():
    assert mcnemar_exact(0, 0) == 1.0
    assert mcnemar_exact(5, 5) == 1.0
    assert mcnemar_exact(0, 10) == pytest.approx(2 * 0.5**10)
    assert mcnemar_exact(10, 0) == pytest.approx(2 * 0.5**10)
    assert mcnemar_exact(2, 8) == pytest.approx(2 * sum(math.comb(10, i) for i in range(3)) / 2**10)
    assert 0 < mcnemar_exact(3, 7) < 1


def test_wilson_interval_is_sane():
    assert wilson(0, 0) == (0.0, 1.0)
    lo, hi = wilson(5, 10)
    assert 0.23 < lo < 0.24 and 0.76 < hi < 0.77
    lo, hi = wilson(0, 10); assert lo == 0.0 and 0.25 < hi < 0.32
    lo, hi = wilson(10, 10); assert hi == 1.0 and 0.68 < lo < 0.75
    assert wilson(50, 100)[1] - wilson(50, 100)[0] < wilson(5, 10)[1] - wilson(5, 10)[0]      # plus de données, intervalle plus étroit


def _pairs(spec):
    return [{"question": f"q{i}", "strict": {"ok": s}, "open": {"ok": o}} for i, (s, o) in enumerate(spec)]


def test_summary_counts_and_conclusiveness():
    s = summarize(_pairs([(True, True)] * 5 + [(False, True)] * 12 + [(False, False)] * 3))
    assert (s["n"], s["strict_ok"], s["open_ok"], s["only_open"], s["only_strict"]) == (20, 5, 17, 12, 0)
    assert s["delta"] == pytest.approx(-0.6) and s["conclusive"] is True and s["p_value"] < 0.01
    few = summarize(_pairs([(False, True)] * 3 + [(True, True)] * 7))
    assert few["conclusive"] is False                      # 3 paires divergentes : jamais conclusif, même à p faible
    same = summarize(_pairs([(True, False)] * 6 + [(False, True)] * 6))
    assert same["conclusive"] is False and same["p_value"] == 1.0
    assert summarize([])["n"] == 0


def test_report_never_claims_an_effect_when_inconclusive():
    res = {"summary": summarize(_pairs([(False, True)] * 2 + [(True, True)] * 4)), "llm_calls": 12}
    text = render_report(res, "dataset.jsonl", "llama3.2")
    assert "NON CONCLUANT" in text and "Conclusif**" not in text and "-33 points" in text.replace("−", "-")
    big = {"summary": summarize(_pairs([(False, True)] * 14 + [(True, True)] * 6)), "llm_calls": 40}
    assert "**Conclusif**" in render_report(big, "d", "m")


# ── exécution avec un faux modèle ───────────────────────────────────────────

class FakeLLM:
    """Ne produit le bon SQL que s'il VOIT les lignes d'exemple (le mot « Québec » n'est que dans les données)."""

    def __init__(self):
        self.calls = []

    def complete(self, system, prompt):
        self.calls.append(prompt)
        wants_quebec = "Québec" in prompt.split("###QUESTION###")[0]          # présent seulement via les lignes d'exemple
        if "chiffre d'affaires total" in prompt:
            return "SELECT SUM(montant) FROM ventes"                            # question sans valeur : réussit toujours
        region = "Québec" if wants_quebec else "Quebec"
        return f"SELECT SUM(montant) FROM ventes WHERE region = '{region}'"


@pytest.fixture()
def dataset(tmp_path):
    p = tmp_path / "dataset.jsonl"
    p.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in [
        {"question": "Quel est le chiffre d'affaires total ?", "gold_sql": "SELECT SUM(montant) FROM ventes"},
        {"question": "Quel est le chiffre d'affaires au Québec ?", "gold_sql": "SELECT SUM(montant) FROM ventes WHERE region = 'Québec'"},
    ]) + "\n", encoding="utf-8")
    return p


def test_paired_run_measures_the_effect_of_withholding_sample_rows(dataset, monkeypatch):
    monkeypatch.delenv("SOVEREIGN_AI_STRICT", raising=False)
    (dataset.parent / "ventes.csv").write_text("x\n")           # inutile : le chargeur lit eval/ventes.csv
    res = run_compare(FakeLLM(), SMALL.parent / "dataset.jsonl", log=lambda *_: None) if False else None
    # le chargeur prend ventes.csv à côté du paquet eval ; on pointe donc le jeu d'essai vers cette table via son nom
    llm = FakeLLM()
    import eval.compare_strict as cs
    monkeypatch.setattr(cs, "HERE", DATA)
    res = run_compare(llm, dataset, log=lambda *_: None)
    s = res["summary"]
    assert s["n"] == 2 and s["open_ok"] == 2 and s["strict_ok"] == 1
    assert (s["only_open"], s["only_strict"]) == (1, 0) and s["conclusive"] is False
    p = res["pairs"][1]
    assert p["open"]["ok"] and not p["strict"]["ok"] and "Quebec" in p["strict"]["sql"]
    assert res["llm_calls"] == 4 == len(llm.calls)                # 2 questions × 2 bras, aucune étape de rédaction


def test_strict_arm_never_shows_values_open_arm_does(dataset, monkeypatch):
    import eval.compare_strict as cs
    monkeypatch.setattr(cs, "HERE", DATA)
    llm = FakeLLM()
    run_compare(llm, dataset, log=lambda *_: None)
    prompts = llm.calls
    strict_prompts, open_prompts = prompts[0::2], prompts[1::2]        # bras strict d'abord, puis ouvert, pour chaque question
    assert all("Québec" not in p.split("###QUESTION###")[0] and "exemples" not in p for p in strict_prompts)
    assert all("exemples" in p for p in open_prompts)


def test_environment_is_restored_and_resume_skips_done_pairs(dataset, tmp_path, monkeypatch):
    import eval.compare_strict as cs
    monkeypatch.setattr(cs, "HERE", DATA)
    monkeypatch.setenv("SOVEREIGN_AI_STRICT", "keep-me")
    out = tmp_path / "res.json"
    llm = FakeLLM()
    run_compare(llm, dataset, out=out, log=lambda *_: None)
    assert os.environ["SOVEREIGN_AI_STRICT"] == "keep-me"
    monkeypatch.delenv("SOVEREIGN_AI_STRICT")
    n_first = len(llm.calls)
    run_compare(llm, dataset, out=out, log=lambda *_: None)             # reprise : tout est déjà mesuré
    assert len(llm.calls) == n_first and "SOVEREIGN_AI_STRICT" not in os.environ
    assert len(json.loads(out.read_text())["pairs"]) == 2


def test_a_model_failure_counts_as_a_failed_arm_with_its_cause(dataset, monkeypatch):
    import eval.compare_strict as cs
    monkeypatch.setattr(cs, "HERE", DATA)

    class Down:
        def complete(self, system, prompt):
            raise TimeoutError("modèle indisponible")

    res = run_compare(Down(), dataset, log=lambda *_: None)
    assert res["summary"]["strict_ok"] == 0 and res["summary"]["open_ok"] == 0
    assert all(p[a]["error"] for p in res["pairs"] for a in ("strict", "open"))


def test_sqlonly_wrapper_does_not_forward_the_answer_step():
    class L:
        n = 0
        def complete(self, s, p): L.n += 1; return "x"
    w = SqlOnly(L(), "ANSWER")
    assert w.complete("ANSWER", "p") == "" and L.n == 0
    assert w.complete("SQL", "p") == "x" and L.n == 1 and w.calls == 1


def test_load_items_sampling_is_reproducible_and_bounded():
    a = load_items(DATA / "dataset_large.jsonl", 10, seed=1)
    b = load_items(DATA / "dataset_large.jsonl", 10, seed=1)
    c = load_items(DATA / "dataset_large.jsonl", 10, seed=2)
    assert a == b and a != c and len(a) == 10
    assert len(load_items(DATA / "dataset_large.jsonl", None, 0)) == 100
    assert len(load_items(SMALL, 50, 0)) == 6


def test_the_large_dataset_tables_load_and_nearly_every_gold_sql_runs():
    from eval.compare_strict import gold_runs, load_store
    store = load_store(DATA / "dataset_large.jsonl")
    assert {"ventes_detail", "clients", "commandes", "employes", "produits"} <= store.tables
    items = load_items(DATA / "dataset_large.jsonl", None, 0)
    failures = [(i["question"], gold_runs(store, i)) for i in items if gold_runs(store, i)]
    assert len(failures) <= 2, failures[:5]                 # les dates sont typées ; le reste est signalé, pas compté


def test_questions_with_a_broken_reference_are_excluded_not_counted_against_the_model(dataset, tmp_path, monkeypatch):
    import eval.compare_strict as cs
    monkeypatch.setattr(cs, "HERE", DATA)
    bad = tmp_path / "bad.jsonl"
    bad.write_text(json.dumps({"question": "Question cassée ?", "gold_sql": "SELECT * FROM table_inexistante"}) + "\n"
                   + dataset.read_text(encoding="utf-8"), encoding="utf-8")
    res = run_compare(FakeLLM(), bad, log=lambda *_: None)
    assert res["summary"]["n"] == 2 and len(res["skipped"]) == 1 and "inexistante" in res["skipped"][0]["reason"].lower() or "table_inexistante" in res["skipped"][0]["reason"]
    assert "exclues" in render_report(res, "d", "m")

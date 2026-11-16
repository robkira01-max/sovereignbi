"""Mesure appariée de l'effet du mode strict sur la précision du SQL (P-070).

Pour chaque question, le MÊME modèle génère le SQL deux fois : mode strict (schéma seul) et mode ouvert (avec lignes
d'exemple). On compare le résultat exécuté au résultat du SQL de référence (execution accuracy, comme run_eval).
L'étape qui rédige la réponse n'est pas appelée (elle n'influence pas le SQL) : une question coûte donc 2 générations.

Usage (modèle choisi comme en production : LLM_PROVIDER, OLLAMA_URL / KIMI_*, LLM_MODEL) :
    python -m eval.compare_strict --limit 20 --out /tmp/strict.json
    python -m eval.compare_strict --dataset eval/dataset_large.jsonl --limit 100 --report /tmp/rapport.md

Reprise : relancer avec le même --out saute les paires déjà mesurées. Aucune donnée réelle : jeux synthétiques seulement.
Lecture : avec peu de paires divergentes (< 10) ou p >= 0,05, le résultat est NON CONCLUANT — ne pas l'annoncer comme un effet.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd

HERE = Path(__file__).parent
ARMS = ("strict", "open")


# ── statistiques (sans dépendance) ──────────────────────────────────────────

def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Intervalle de Wilson à 95 % d'une proportion k/n."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, centre - half), min(1.0, centre + half))


def mcnemar_exact(b: int, c: int) -> float:
    """p bilatéral du test exact de McNemar : b = réussit seulement en strict, c = réussit seulement en ouvert."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2**n
    return min(1.0, 2 * tail)


def summarize(pairs: list[dict]) -> dict:
    n = len(pairs)
    s_ok = sum(p["strict"]["ok"] for p in pairs)
    o_ok = sum(p["open"]["ok"] for p in pairs)
    only_strict = sum(p["strict"]["ok"] and not p["open"]["ok"] for p in pairs)
    only_open = sum(p["open"]["ok"] and not p["strict"]["ok"] for p in pairs)
    p = mcnemar_exact(only_strict, only_open)
    discordant = only_strict + only_open
    return {
        "n": n, "strict_ok": s_ok, "open_ok": o_ok,
        "strict_acc": s_ok / n if n else 0.0, "open_acc": o_ok / n if n else 0.0,
        "strict_ci": wilson(s_ok, n), "open_ci": wilson(o_ok, n),
        "delta": (s_ok - o_ok) / n if n else 0.0,
        "only_strict": only_strict, "only_open": only_open, "p_value": p,
        "conclusive": discordant >= 10 and p < 0.05,
    }


# ── exécution ───────────────────────────────────────────────────────────────

class SqlOnly:
    """Enveloppe d'un LLM : l'étape « réponse » n'est pas envoyée au modèle (elle n'influence pas le SQL)."""

    def __init__(self, llm, answer_system: str):
        self.llm, self.answer_system, self.calls = llm, answer_system, 0

    def complete(self, system: str, prompt: str) -> str:
        if system == self.answer_system:
            return ""
        self.calls += 1
        return self.llm.complete(system, prompt)


def _norm(rows):
    return sorted(tuple(round(v, 4) if isinstance(v, float) else v for v in r) for r in rows)


def _read_csv(path: Path) -> pd.DataFrame:
    """CSV → DataFrame ; les colonnes de date sont typées (les requêtes de référence utilisent year(), dayofweek()…)."""
    df = pd.read_csv(path)
    for col in df.columns:
        if "date" in col.lower() and pd.api.types.is_string_dtype(df[col]):
            parsed = pd.to_datetime(df[col], errors="coerce")
            if parsed.notna().mean() >= 0.9:
                df[col] = parsed
    return df


def load_store(dataset: Path):
    from app.data.duckdb_store import DataStore

    store = DataStore()
    fx = HERE / "fixtures"
    if "large" in dataset.name:
        store.load_dataframe("ventes_detail", _read_csv(fx / "large_schema.csv"))
        for name in ("clients", "commandes", "employes", "produits"):
            store.load_dataframe(name, _read_csv(fx / f"{name}.csv"))
    else:
        store.load_dataframe("ventes", _read_csv(HERE / "ventes.csv"))
    return store


def load_items(dataset: Path, limit: int | None, seed: int) -> list[dict]:
    items = [json.loads(l) for l in dataset.read_text(encoding="utf-8").splitlines() if l.strip()]
    if limit is not None and limit < len(items):
        random.Random(seed).shuffle(items)          # échantillon reproductible, non biaisé par l'ordre du fichier
        items = items[:limit]
    return items


def gold_runs(store, item: dict) -> str | None:
    """None si la requête de référence s'exécute ; sinon la cause (la question est alors exclue, pas comptée contre le modèle)."""
    try:
        store.execute(item["gold_sql"])
        return None
    except Exception as e:  # noqa: BLE001
        return f"{type(e).__name__}: {str(e)[:100]}"


def run_arm(graph, store, item: dict, strict: bool) -> dict:
    prev = os.environ.get("SOVEREIGN_AI_STRICT")
    os.environ["SOVEREIGN_AI_STRICT"] = "1" if strict else "0"
    t0 = time.perf_counter()
    try:
        _, gold = store.execute(item["gold_sql"])
        s = graph.invoke({"question": item["question"]})
        ok = not s.get("error") and _norm(s.get("rows", [])) == _norm(gold)
        return {"ok": bool(ok), "sql": s.get("sql"), "attempts": s.get("attempts"), "error": s.get("error"),
                "seconds": round(time.perf_counter() - t0, 1)}
    except Exception as e:  # noqa: BLE001 - une panne du modèle compte comme échec, avec sa cause
        return {"ok": False, "sql": None, "attempts": None, "error": f"{type(e).__name__}: {str(e)[:160]}",
                "seconds": round(time.perf_counter() - t0, 1)}
    finally:
        if prev is None:
            os.environ.pop("SOVEREIGN_AI_STRICT", None)
        else:
            os.environ["SOVEREIGN_AI_STRICT"] = prev


def run_compare(llm, dataset: Path, limit: int | None = None, seed: int = 0, out: Path | None = None,
                semantic: str = "", log=print) -> dict:
    from app.pipeline.graph import ANSWER_SYSTEM, build_graph

    store = load_store(dataset)
    items = load_items(dataset, limit, seed)
    wrapped = SqlOnly(llm, ANSWER_SYSTEM)
    graph = build_graph(wrapped, store, semantic)
    done: dict[str, dict] = {}
    if out and out.exists():
        done = {p["question"]: p for p in json.loads(out.read_text(encoding="utf-8")).get("pairs", [])}
    pairs: list[dict] = []
    skipped: list[dict] = []
    for i, item in enumerate(items, 1):
        bad = gold_runs(store, item)
        if bad:                                   # référence inexécutable : exclue et signalée
            skipped.append({"question": item["question"], "reason": bad})
            log(f"[{i}/{len(items)}] exclue (référence inexécutable) : {item['question'][:60]}")
            continue
        pair = done.get(item["question"])
        if pair is None:
            pair = {"question": item["question"], "gold_sql": item["gold_sql"]}
            for arm in ARMS:                      # les deux bras se suivent : une interruption laisse toujours des paires complètes
                pair[arm] = run_arm(graph, store, item, strict=(arm == "strict"))
            done[item["question"]] = pair
            if out:
                out.write_text(json.dumps({"dataset": dataset.name, "seed": seed, "pairs": list(done.values())}, ensure_ascii=False, indent=1),
                               encoding="utf-8")
            log(f"[{i}/{len(items)}] strict={'✅' if pair['strict']['ok'] else '❌'} ouvert={'✅' if pair['open']['ok'] else '❌'}  {item['question'][:70]}")
        pairs.append(pair)
    return {"pairs": pairs, "skipped": skipped, "summary": summarize(pairs), "llm_calls": wrapped.calls}


def render_report(res: dict, dataset: str, model: str) -> str:
    s = res["summary"]
    pc = lambda x: f"{x * 100:.0f} %"                                          # noqa: E731
    ci = lambda t: f"[{t[0] * 100:.0f} – {t[1] * 100:.0f} %]"                  # noqa: E731
    verdict = ("**Conclusif** : la différence est statistiquement significative." if s["conclusive"] else
               "**NON CONCLUANT** : trop peu de paires divergentes ou différence non significative. Ne pas annoncer d'effet.")
    return f"""# Effet du mode strict sur la précision SQL

Jeu : `{dataset}` · modèle : `{model}` · {s['n']} questions appariées · {res['llm_calls']} appels au modèle (génération SQL seulement).

| Mode | Réussites | Précision | IC 95 % (Wilson) |
|---|---|---|---|
| Strict (schéma seul) | {s['strict_ok']}/{s['n']} | {pc(s['strict_acc'])} | {ci(s['strict_ci'])} |
| Ouvert (avec lignes d'exemple) | {s['open_ok']}/{s['n']} | {pc(s['open_acc'])} | {ci(s['open_ci'])} |

Écart (strict − ouvert) : **{s['delta'] * 100:+.0f} points**. Paires divergentes : {s['only_open']} réussies seulement en ouvert, {s['only_strict']} seulement en strict.
Test exact de McNemar : p = {s['p_value']:.3f}.

{verdict}

{('Questions exclues (requête de référence inexécutable sur les données) : ' + str(len(res.get('skipped', []))) + '.') if res.get('skipped') else ''}

Limites : un seul modèle, un seul tirage de réponses par question (la génération est aléatoire) ; jeu synthétique ; l'étape de rédaction de la réponse n'est pas évaluée.
"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset", type=Path, default=HERE / "dataset.jsonl")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", type=Path, default=None, help="JSON de résultats (reprise automatique)")
    ap.add_argument("--report", type=Path, default=None, help="rapport Markdown")
    a = ap.parse_args(argv)
    from app.llm import get_llm_client
    from app.pipeline.graph import load_semantic

    llm = get_llm_client()
    res = run_compare(llm, a.dataset, a.limit, a.seed, a.out, semantic=load_semantic())
    model = os.environ.get("KIMI_MODEL" if os.environ.get("LLM_PROVIDER", "ollama").lower() == "kimi" else "LLM_MODEL", "défaut")
    text = render_report(res, a.dataset.name, model)
    print("\n" + text)
    if a.report:
        a.report.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())

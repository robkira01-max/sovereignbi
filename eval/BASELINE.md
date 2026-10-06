# Ligne de base — SovereignBI Sprint 1

Date : 2026-10-06  
Modèle testé : `llama3.2:latest` (2,0 Go, CPU uniquement)  
Modèle cible : `qwen2.5-coder:32b` (non disponible sur cette machine)

## Résultat partiel (test manuel — 1 question)

| Question | SQL généré | Correct |
|---|---|---|
| Quel est le chiffre d'affaires total ? | `SELECT SUM(montant) FROM ventes` | ✅ |

## Contrainte de performance

- `llama3.2:latest` : ~111 s par requête sur CPU (inference lente).
- L'éval complète (6 questions × jusqu'à 3 tentatives = 18 appels max) dépasse
  le timeout httpx de 300 s sur les appels tardifs (Ollama sous charge cumulative).
- **Score automatisé indisponible sur cette machine avec ce modèle.**

## Ligne de base à établir (action requise)

1. Déployer `qwen2.5-coder:32b` ou `deepseek-coder:33b` sur une machine avec GPU.
2. Lancer `LLM_MODEL=<modèle> python -m eval.run_eval` et reporter le score ici.
3. Objectif Sprint 2 : score mesuré sur jeu de 100 paires (schéma large ≥ 50 colonnes).

## Harnais validé

- `run_eval()` avec `FakeLLM(gold_sqls)` → score = 1.0 ✅ (test automatisé `test_eval_harness_scores_perfect_with_gold_llm`)
- Logique d'exécution et de comparaison des résultats (`_norm`) : correcte.
- Le harnais est prêt ; seul le modèle local rapide manque pour mesurer la précision réelle.

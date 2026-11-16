# Ligne de base — MizanBI Sprint 1

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


## Mesure de l'effet du mode strict (P-070) — outil prêt, mesure à faire

`python -m eval.compare_strict --dataset eval/dataset_large.jsonl --limit 100 --out strict.json --report rapport.md`

Même modèle, mêmes questions, deux modes (strict = schéma seul ; ouvert = avec 3 lignes d'exemple par table). Compare l'**execution accuracy** (résultat du SQL généré = résultat du SQL de référence). Statistiques : intervalles de Wilson, test exact de McNemar ; le rapport indique **NON CONCLUANT** s'il y a moins de 10 paires divergentes ou p ≥ 0,05. Reprise automatique (`--out`), échantillon reproductible (`--seed`), questions à référence inexécutable exclues et signalées. L'étape de rédaction de la réponse n'est pas appelée (elle n'influence pas le SQL).

**Ce qu'il faut :** le modèle réellement visé (`LLM_PROVIDER`, `KIMI_*` ou `LLM_MODEL`), de préférence une API ou un GPU. 100 questions × 2 modes = 200 générations : quelques minutes avec une API, **plus de 20 heures sur cette machine** (mesuré le 2026-11-15 : 7 à 12 minutes par génération, `llama3.2` sur 4 CPU sans GPU, machine chargée).

**Seul essai réalisé (2026-11-15) : un test de fonctionnement, PAS une mesure.** `llama3.2:latest`, jeu de 6 questions, 1 paire menée à terme (la seconde a été coupée par le délai de 25 min) : en strict le modèle a inventé une jointure sur une table inexistante (`clients`, refusée par le garde-fou SQL) ; en ouvert il a réussi. **Une paire n'établit rien** : cela montre seulement que l'outil tourne de bout en bout avec le vrai client Ollama. Ne pas en tirer d'effet du mode strict.

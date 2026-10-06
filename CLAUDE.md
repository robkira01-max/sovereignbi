# SovereignBI — consignes pour Claude Code

Lis `PLAN.md` en entier avant toute action : c'est la source de vérité (benchmark, dashboards, sprints, politique DeepSeek).

- Sprint 1 est livré. Ne passe au sprint suivant qu'avec l'accord de Robleh.
- Après tout changement de pipeline/prompt/modèle : `pytest` puis `python -m eval.run_eval`. Pas de régression sans justification.
- Utilise des sous-agents avec des périmètres de fichiers distincts (explore, plan, tests/éval, sécurité adversariale, front/dashboards en worktree séparé).
- DeepSeek : dev uniquement, données synthétiques, via `tools/dev_llm.py`. `app/` n'importe jamais `tools/` et ne contient aucun appel externe.
- Licences permissives uniquement (MIT/Apache/BSD) ; tenir `THIRD_PARTY.md` à jour.
- Code en anglais, documentation et UI en français.

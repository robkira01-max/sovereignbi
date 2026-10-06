# THIRD_PARTY.md — Inventaire des dépendances tierces

> Politique : licences MIT, Apache 2.0 ou BSD uniquement. Aucune dépendance GPL/AGPL embarquée dans le produit livré.

| Bibliothèque | Version min | Licence | Usage |
|---|---|---|---|
| fastapi | 0.115 | MIT | API HTTP |
| uvicorn[standard] | 0.30 | BSD | Serveur ASGI |
| python-multipart | 0.0.9 | Apache 2.0 | Upload de fichiers |
| httpx | 0.27 | BSD | Client HTTP vers Ollama local |
| duckdb | 1.0 | MIT | Moteur SQL embarqué |
| pandas | 2.2 | BSD | Lecture Excel/CSV |
| openpyxl | 3.1 | MIT | Lecture .xlsx |
| sqlglot | 25.0 | MIT | Parsing et validation SQL |
| langgraph | 0.2 | MIT | Orchestration pipeline |
| pyyaml | 6.0 | MIT | Modèle sémantique YAML |
| xlrd | 2.0 | BSD | Lecture .xls legacy |
| psycopg2-binary | 2.9 | LGPL v3 | Connecteur PostgreSQL — usage dynamique uniquement (driver), non embarqué dans le produit livré. Acceptable pour les règles du projet. |
| pytest | 8.0 | MIT | Tests (dev uniquement) |

## Modèles LLM (runtime — choix par l'administrateur)

| Modèle candidat | Licence | Notes |
|---|---|---|
| Qwen2.5-Coder 32B | Apache 2.0 | Recommandé pour machines avec GPU |
| deepseek-coder:6.7b | MIT | Léger, CPU convenable |
| llama3.2 | Llama 3.2 Community (Meta) | **Vérifier restrictions commerciales avant usage** |
| OmniSQL 7B/14B/32B | À vérifier | Vérifier la licence sur HuggingFace avant tout usage commercial |
| DeepSeek V3.2 (poids ouverts) | MIT (V3.2 — vérifier sur fiche officielle) | Candidat Ollama ; distillations héritent de la licence de base |

> **Règle** : le choix du modèle de production se fait **par le score d'éval**, pas par réputation. Vérifier la licence sur la fiche officielle du modèle avant tout usage commercial.

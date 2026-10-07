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
| qdrant-client | 1.9 | Apache 2.0 | Store vectoriel in-memory (schema linking) |
| scikit-learn | 1.4 | BSD | TF-IDF fallback embedder (sans réseau) |
| sentence-transformers | 3.0 | Apache 2.0 | BGE-M3 embedder (chargement lazy, production) |
| streamlit | 1.35 | Apache 2.0 | Interface utilisateur web |
| plotly | 5.0 | MIT | Graphiques interactifs (Streamlit UI) |
| fpdf2 | 2.7 | MIT | Génération de PDF (export résultats) |
| pymysql | 1.1 | MIT | Connecteur MySQL (pure Python, aucun driver système) |
| pymssql | 2.3 | LGPL v2.1 (FreeTDS) | Connecteur SQL Server — usage dynamique uniquement (driver), non embarqué dans le produit livré. Même raisonnement que psycopg2. |
| pypdf | 4.0 | MIT | Extraction texte PDF (RAG documentaire) |
| python-docx | 1.1 | MIT | Extraction texte DOCX (RAG documentaire) |
| pytest | 8.0 | MIT | Tests (dev uniquement) |
| playwright | 1.44 | Apache 2.0 | Tests E2E navigateur (dev uniquement) |

## Connecteurs optionnels (non installés par défaut — import lazy)

| Bibliothèque | Licence | Usage |
|---|---|---|
| snowflake-connector-python | Apache 2.0 | Connecteur Snowflake — importer manuellement : `pip install snowflake-connector-python` |
| google-cloud-bigquery | Apache 2.0 | Connecteur BigQuery — importer manuellement : `pip install google-cloud-bigquery` |
| pymongo | Apache 2.0 | Connecteur MongoDB — importer manuellement : `pip install pymongo` |

## Modèles LLM (runtime — choix par l'administrateur)

| Modèle candidat | Licence | Notes |
|---|---|---|
| Qwen2.5-Coder 32B | Apache 2.0 | Recommandé pour machines avec GPU |
| deepseek-coder:6.7b | MIT | Léger, CPU convenable |
| llama3.2 | Llama 3.2 Community (Meta) | **Vérifier restrictions commerciales avant usage** |
| OmniSQL 7B/14B/32B | À vérifier | Vérifier la licence sur HuggingFace avant tout usage commercial |
| DeepSeek V3.2 (poids ouverts) | MIT (V3.2 — vérifier sur fiche officielle) | Candidat Ollama ; distillations héritent de la licence de base |

> **Règle** : le choix du modèle de production se fait **par le score d'éval**, pas par réputation. Vérifier la licence sur la fiche officielle du modèle avant tout usage commercial.

## Frontend (Sprint 9)

| Bibliothèque | Version min | Licence | Usage |
|---|---|---|---|
| react | 18.x | MIT | UI SPA |
| react-dom | 18.x | MIT | Rendu DOM React |
| recharts | 2.x | MIT | Graphiques interactifs (BarChart, LineChart, PieChart) |
| vite | 5.x | MIT | Bundler frontend |
| @vitejs/plugin-react | 4.x | MIT | Plugin React pour Vite |
| vitest | 1.x | MIT | Tests unitaires frontend |
| @testing-library/react | 16.x | MIT | Tests composants React |
| @testing-library/jest-dom | 6.x | MIT | Matchers DOM pour Vitest |
| typescript | 5.x | Apache 2.0 | Typage statique JavaScript |

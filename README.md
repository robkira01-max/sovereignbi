# SovereignBI

**Outil BI conversationnel 100 % local — souveraineté des données garantie.**

Posez vos questions en français (ou anglais), obtenez du SQL validé, des résultats et une réponse en langage naturel — sans qu'une seule donnée ne quitte votre infrastructure.

---

## Fonctionnalités

| Fonctionnalité               | Détail                                                   |
|------------------------------|----------------------------------------------------------|
| Text-to-SQL                  | LangGraph 3 nœuds : génération → validation → réponse   |
| LLM local                    | Ollama (Mistral, LLaMA, etc.) — aucun appel externe      |
| Connecteurs de données       | DuckDB, PostgreSQL, Excel, MySQL, MSSQL, Snowflake, BigQuery, MongoDB |
| Couche sémantique YAML       | Métriques, dimensions, jointures, glossaire              |
| RAG documentation            | Recherche dans vos PDF/DOCX pour enrichir les réponses   |
| Few-shot learning            | Apprentissage automatique des corrections utilisateur    |
| Score de confiance           | 4 facteurs, grade A–F, certificat signé HMAC             |
| RBAC                         | viewer / editor / admin via `X-Api-Key`                  |
| Rate limiting                | 60 rpm par IP, headers `X-RateLimit-*`                   |
| Export                       | Excel et PDF avec avertissement IA                       |
| Dashboards                   | Tableaux de bord persistants                             |
| Alertes                      | Règles SQL avec seuils et notifications                  |
| Multi-tenant                 | Organisations isolées                                    |
| Conformité                   | Rapport Loi 25 / PIPEDA exportable                       |
| Monitoring                   | Prometheus + Grafana + Helm chart Kubernetes             |
| Frontend                     | React SPA (Vite + TypeScript)                            |

---

## Démarrage rapide

```bash
# 1. Prérequis : Python 3.11+, Ollama installé et démarré
# 2. Cloner et installer
git clone <repo_url>
cd sovereignbi
make install

# 3. Configurer
cp .env.example .env
# Éditer .env : clés RBAC, modèle Ollama, etc.

# 4. Démarrer
make run
# → http://localhost:8000
```

### Avec Docker Compose

```bash
docker compose up
# → FastAPI sur :8000, UI Streamlit sur :8501
```

---

## Variables d'environnement clés

| Variable                  | Défaut          | Description                             |
|---------------------------|-----------------|------------------------------------------|
| `SOVEREIGN_ADMIN_KEY`     | —               | Clé admin RBAC **(obligatoire)**         |
| `SOVEREIGN_EDITOR_KEY`    | —               | Clé editor RBAC                          |
| `SOVEREIGN_VIEWER_KEY`    | —               | Clé viewer RBAC                          |
| `SOVEREIGN_EMBED_SECRET`  | —               | Secret tokens iframe (≥ 32 chars)        |
| `OLLAMA_BASE_URL`         | `http://localhost:11434` | URL du serveur Ollama          |
| `OLLAMA_MODEL`            | `mistral`       | Modèle LLM à utiliser                   |
| `SOVEREIGN_EMBEDDER`      | `bge-m3`        | Embeddings (`tfidf` pour les tests)      |
| `SOVEREIGN_RATE_LIMIT_RPM`| `60`            | Requêtes / minute par IP                |

Voir `.env.example` pour la liste complète.

---

## Tests

```bash
make test               # tests unitaires (rapides, sans DB)
make test-integration   # tests d'intégration (nécessite Docker)
make lint               # ruff check + format
```

---

## Architecture

```
sovereignbi/
├── app/
│   ├── api/            middleware (rate limit, sécurité, version)
│   ├── alerts/         règles d'alerte SQL
│   ├── cache/          cache LRU requêtes
│   ├── compliance/     rapport Loi 25/PIPEDA
│   ├── connectors/     PostgreSQL, MySQL, MSSQL, Snowflake, BigQuery, MongoDB
│   ├── data/           DuckDB store
│   ├── embed/          tokens iframe HMAC
│   ├── learning/       few-shot retriever
│   ├── llm/            client Ollama (disjoncteur)
│   ├── monitoring/     métriques Prometheus
│   ├── multitenancy/   organisations multi-tenant
│   ├── pipeline/       LangGraph (generate_sql → validate_execute → answer)
│   ├── rag/            DocStore PDF/DOCX + OCR
│   ├── routers/        endpoints FastAPI
│   ├── security/       RBAC, audit démarrage, utilitaires clés
│   └── templates/      wizard YAML
├── eval/               évaluation text-to-SQL
├── frontend/           React SPA (Vite + TypeScript)
├── helm/               chart Kubernetes
├── semantic/           modèles YAML couche sémantique
├── tests/              pytest (unitaires + intégration)
├── tools/              outils de développement (DeepSeek dev uniquement)
└── ui/                 interface Streamlit
```

---

## Sécurité

Voir [docs/SECURITY.md](docs/SECURITY.md).

**Principe fondamental** : SovereignBI ne fait aucun appel réseau externe par défaut.
`app/` n'importe jamais `tools/` et ne contient aucun appel à un service tiers.

---

## Conformité

- **Loi 25 (Québec)** — données traitées localement
- **PIPEDA (Canada)** — consentement, finalité limitée, accès sécurisé
- Rapport exportable : `GET /v1/compliance/report` (rôle admin)

---

## Licence

MIT — voir [LICENSE](LICENSE).

SovereignBI est un outil d'aide à la décision. Il ne remplace pas un analyste de données ni un responsable de la conformité. Vérifiez toujours les résultats avant toute décision critique.

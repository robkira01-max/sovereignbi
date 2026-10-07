# Changelog — SovereignBI

Toutes les modifications notables sont documentées ici.
Format : [Unreleased] / [version] — date / types : Added, Changed, Fixed, Security, Removed.

---

## [1.0.0] — 2026-10-05

### Added — Sprint 22 (productionisation finale)
- `app/security/audit.py` : audit de configuration au démarrage (SEC-001→SEC-006)
- `app/security/secrets.py` : `generate_api_key`, `hash_key_for_log`, `validate_key_strength`
- `app/api/middleware.py` : en-têtes `X-RateLimit-Limit/Remaining/Reset` sur chaque réponse
- Appel de l'audit au démarrage via `lifespan` dans `app/main.py`
- `docs/CHANGELOG.md`, `docs/SECURITY.md`, `README.md`, `LICENSE` (MIT)

### Added — Sprint 21
- Helm chart `helm/sovereignbi/` avec probes Kubernetes liveness/readiness
- Intégration Prometheus — métriques `/metrics`
- `docs/grafana-dashboard.json` tableau de bord prêt à l'emploi

### Added — Sprint 20
- Certificat de précision 5 critères (grade A–F, signature HMAC)
- `GET /v1/accuracy/certificate` — rapport téléchargeable

### Added — Sprint 19
- Onboarding guidé (wizard 4 étapes)
- Démo sandbox reproductible avec données fictives

### Added — Sprint 18
- Marketplace de templates YAML (`GET/POST /v1/marketplace/templates`)
- Catalogue partageable avec métadonnées de licence

### Added — Sprint 17
- Cache LRU requêtes (`app/cache/query_cache.py`, `GET/DELETE /v1/cache`)
- En-têtes `X-Cache: HIT|MISS` et statistiques

### Added — Sprint 16
- Scaffold Playwright E2E (`e2e/`)
- Tests de fumée `/health`, `/ready`, pipeline complet

### Added — Sprint 15
- Module conformité Loi 25/PIPEDA (`app/compliance/`)
- `GET /v1/compliance/report` — rapport JSON exportable

### Added — Sprint 14
- Connecteurs Snowflake, BigQuery, MongoDB (`app/connectors/`)
- `POST /connectors/test` — vérification de connectivité

### Added — Sprint 13
- API REST versionnée v1 (`/v1/`) avec préfixe stable
- Middleware `ApiVersionMiddleware` — en-tête `X-API-Version`
- Middleware `SecurityHeadersMiddleware` — CSP, HSTS, X-Frame-Options

### Added — Sprint 12
- Alertes monitoring (`app/alerts/`) — règles SQL, seuils, notifications
- `POST/GET/DELETE /alerts/rules`

### Added — Sprint 11
- Multi-tenant organisations (`app/multitenancy/`)
- `POST/GET /orgs/` — création et gestion des organisations

### Added — Sprint 10
- Extraction avancée PDF/DOCX avec tableaux
- OCR fallback via pytesseract (gracieux si Tesseract absent)

### Added — Sprint 9
- Frontend React SPA Vite + TypeScript (`frontend/`)
- Pages Chat, Dashboard, Upload, Login

### Added — Sprint 8
- Wizard de création de templates YAML (4 étapes)
- Tokens embed HMAC-SHA256 signés avec TTL et scopes
- Catalogue de templates (`GET /templates/catalogue`)

### Added — Sprint 7
- Connecteurs MySQL et MSSQL (`app/connectors/`)
- Pipeline RAG documentation (`app/rag/doc_store.py`)
- Score de confiance 4 facteurs (`app/pipeline/confidence.py`)

### Added — Sprint 6
- RBAC roles viewer/editor/admin via `X-Api-Key`
- Export Excel et PDF avec avertissement IA
- SBOM `THIRD_PARTY.md`
- `RateLimitMiddleware` — fenêtre glissante 60 rpm par IP

### Added — Sprint 5
- Apprentissage few-shot (`app/learning/few_shot.py`)
- Rapport d'erreurs structuré
- Versionnage des requêtes

### Added — Sprint 4
- Interface Streamlit (`ui/`)
- Tableaux de bord persistants
- Boucle de feedback utilisateur

### Added — Sprint 3
- Couche sémantique YAML v2 (`semantic/`)
- Embeddings TF-IDF (test) / BGE-M3 (production)
- Recherche hybride lexicale + vectorielle

### Added — Sprint 2
- Connecteurs PostgreSQL et Excel
- Jeu de 100 paires question/SQL d'évaluation

### Added — Sprint 1
- Squelette initial : FastAPI, DuckDB, Ollama, `sql_guard`, pipeline LangGraph 3 nœuds
- Infrastructure Docker Compose, Makefile, CI GitHub Actions

---

## [0.1.0] — 2026-09-xx

- Initialisation du dépôt

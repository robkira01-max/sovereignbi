# SovereignBI — Plan de développement et de commercialisation

> **Pour Claude Code** : lis ce fichier en entier avant d'agir, puis `CLAUDE.md`. Travaille sprint par sprint, valide chaque sprint par ses critères de succès, et ne passe au suivant qu'avec l'accord de Robleh.

Slogan : « L'IA vient à vos données, pas l'inverse. »
Vocation : produit **commercialisé** (BI conversationnelle auto-hébergée, hors ligne, souveraine). Développeur solo.

---

## 0. Instructions d'exécution pour Claude Code

### Règles de travail
1. **Mesurer avant d'améliorer.** Chaque changement touchant prompts, modèle, schéma ou pipeline est suivi de `python -m eval.run_eval`. Aucune régression sur le jeu fixe n'est acceptée sans justification écrite.
2. **Tests d'abord** (`pytest`) ; le sprint 1 est livré et vert (18 tests). Ne pas le réécrire, l'étendre.
3. **Utilise toutes les ressources disponibles** : lecture de la doc officielle (WebSearch/WebFetch), skills installés (tests, audit de sécurité FastAPI/Docker, déploiement, design front, revue de code, documentation), serveurs MCP utiles, liste de tâches (TaskCreate/TaskUpdate) pour chaque sprint. Si un skill ou outil cité n'existe pas dans ton environnement, continue sans lui.
4. **Utilise des sous-agents** pour paralléliser, chacun avec un périmètre de fichiers distinct (pas de conflit) et un compte rendu court :
   - *Explore* : cartographier le code avant chaque sprint.
   - *Plan* : proposer l'architecture d'un sprint avant de coder (sprints 2, 3, 4).
   - *Tests/éval* : agrandir le jeu d'éval et écrire les tests, dans un worktree séparé.
   - *Sécurité adversariale* : tenter d'exfiltrer ou de contourner `sql_guard`, injections de prompt via cellules Excel/PDF ; livre un rapport, pas de correctif silencieux.
   - *Front/dashboards* : implémenter l'UI et le moteur de dashboards dans son propre worktree.
   L'agent principal intègre, relance les tests et reste responsable du résultat final.
5. **Pas de dépendance non vérifiée** : chaque nouvelle bibliothèque est contrôlée (licence MIT/Apache/BSD uniquement, pas de GPL/AGPL embarquée dans le produit) et ajoutée à `THIRD_PARTY.md`.
6. **Langue** : code et identifiants en anglais, documentation et interface en français (anglais en second).

### Politique DeepSeek (et modèles externes) — à respecter strictement
DeepSeek peut être utilisé **comme assistant de développement pour certaines tâches**, jamais dans le produit livré par défaut.

| Autorisé (temps de dev) | Interdit |
|---|---|
| Générer des paires question/SQL **sur schémas synthétiques** pour le jeu d'éval | Toute donnée, schéma ou fichier d'un client ou d'un pilote |
| Seconde opinion de revue de code, brouillons de tests, docstrings, traductions | Secrets, clés, identifiants, configuration de déploiement |
| Comparer des idées de prompts | Tout import d'un client externe dans `app/` |

Règles techniques :
- Le code d'appel vit dans `tools/dev_llm.py`, clé via `DEEPSEEK_API_KEY` (jamais commitée). **`app/` n'importe jamais `tools/`**. Ajouter un test CI qui échoue si `app/` contient un nom d'hôte externe ou un import de `tools`.
- Toute sortie DeepSeek est **vérifiée par exécution ou par test** (les paires SQL sont validées en exécutant le SQL sur DuckDB ; jamais prises pour argent comptant).
- L'API hébergée de DeepSeek traite les données hors du Canada : elle est **incompatible** avec des données personnelles (Loi 25) et avec le marché gouvernemental visé. Synthétique seulement.
- **Au runtime**, les poids ouverts DeepSeek servis par Ollama sont un candidat parmi d'autres (le guide consulté indique des poids sous licence MIT pour V3.2 ; **vérifier la licence sur la fiche officielle du modèle** avant tout usage commercial, les versions distillées héritent de la licence de leur modèle de base). Le choix du modèle se fait **par le score d'éval**, pas par réputation.

---

## 1. Benchmark : ce qui se fait dans le monde

### 1.1 Concurrents et références
| Acteur | Positionnement | Déploiement / licence | Prix indicatif | Limite pour nous |
|---|---|---|---|---|
| ThoughtSpot | Recherche en langage naturel, entreprise | SaaS | 100 k–500 k$+/an | Cher, déploiement 3–6 mois |
| Power BI Copilot | Intégré à Microsoft Fabric | Cloud | Capacité Fabric F64 ≈ 6 400 $/mois + licences | Dépend du modèle sémantique existant, données dans le cloud Microsoft |
| Tableau Pulse | Digests de métriques automatisés | SaaS | n.d. | N'interroge que les données modélisées Tableau |
| Querio, Hex, Sigma, Omni, Looker+Gemini | Analytique conversationnelle moderne | SaaS | Querio ≈ 14 k$/an ; Hex 36–75 $/éditeur/mois | Cloud ; couche sémantique lourde (Looker) |
| **Wren AI** | BI générative **open core** : couche sémantique (MDL), RBAC, dashboards, 22+ sources | Cœur Apache 2.0 + parties AGPL-3.0 | Gratuit / commercial | Concurrent direct n°1 ; support Ollama non confirmé dans ce que j'ai lu |
| **Vanna** (≈ 20 k étoiles) | Bibliothèque text-to-SQL par RAG | MIT | Gratuit | Pas de gouvernance, sémantique à curer à la main |
| Metabase | BI classique, IA en ajout | AGPL v3 ; white-label et embedding interactif **dès Pro (575 $/mois)** ; Enterprise ≈ 20 k$/an | Voir gauche | Licence contraignante pour la revente |
| Apache Superset | BI open source | **Apache 2.0**, SDK d'embedding | Gratuit | Pas conversationnel |
| Cube Core | Couche sémantique + API SQL/REST/GraphQL | Apache 2.0 / MIT | Gratuit | Contrôles d'accès avancés probablement commerciaux (à vérifier) |

Note : le comparatif de prix provient d'un blog éditeur (Querio) qui indique qu'aucun de ces outils n'offre d'auto-hébergement documenté. Power BI Report Server existe pourtant en on-premise, sans Copilot à ma connaissance : **à vérifier avant d'écrire « jamais offline » dans le marketing**.

### 1.2 État de l'art de la précision text-to-SQL
- **BIRD** : annonce Google Gemini-SQL2 à **80,04 %** (juin 2026), vs ≈ 77,2 % (Gemini-SQL précédent), ≈ 76,5 % (AWS Q-SQL), ≈ 70,1 % (Claude Opus 4.6), humain 92,96 %. *Aucun rapport technique ni API publié : non vérifiable.*
- **Modèles ouverts** : OmniSQL (7B/14B/32B) ≈ **64–65 %** sur BIRD dev en glouton, **66–67 %** avec vote majoritaire ; ≈ 88–90 % sur Spider test. Ordre de grandeur de ce qu'un modèle local peut viser.
- **Spider 2.0 (entreprise réelle)** : ≈ **10–20 %** contre ≈ 90 % sur Spider 1.0 ; schémas de 812 colonnes en moyenne. Source secondaire. **Les scores académiques surestiment fortement la précision sur des bases réelles.**
- **Couche sémantique** : étude arXiv (100 questions, ClickHouse, 3 modèles de pointe) : **45–50 % → 68–69 %** avec un simple document markdown de 4 Ko (métriques, conventions, règles de désambiguïsation) ; >80 % des échecs viennent du *schema linking* et de la logique métier. Un article de dbt Labs (éditeur) rapporte 90 → 98 % et 84 → 100 % sur les requêtes couvertes par la couche sémantique.
- Point clé : en text-to-SQL pur, l'échec ressemble à une **réponse plausible mais fausse** ; avec une couche sémantique, l'échec est visible (erreur ou refus).

### 1.3 Ce qui peut être amélioré = notre différenciation
1. **Couche sémantique de première classe** (gain mesuré +17 à +23 points) plutôt que « un LLM + le schéma ».
2. **S'abstenir plutôt qu'halluciner** : demande de clarification, SQL toujours visible (dry-run), provenance de chaque chiffre, score de confiance.
3. **Souveraineté réelle** : 100 % hors ligne, français natif, pensé Loi 25 / LPRPDE (transferts hors Québec = évaluation des facteurs relatifs à la vie privée ; sanctions jusqu'à 25 M$ ou 4 % du chiffre d'affaires mondial).
4. **« Certificat de précision » sur les données du client** : l'harnais d'éval est livré et construit un jeu de test à partir des questions validées du client. Personne ne le fait bien.
5. **Excel réel** (en-têtes multiples, cellules fusionnées) traité comme fonctionnalité centrale.
6. **Créneau de prix** : entre Querio (≈ 14 k$) et ThoughtSpot (100 k$+), et sans les coûts cachés de Metabase (≈ 15–20 k$/an d'infra et de maintenance rapportés).
7. **Dashboards par client** (section 3) : templates propres à chaque personne et société.

---

## 2. Architecture (inchangée, voir code du sprint 1)

Pipeline LangGraph à **3 nœuds** : `generate_sql` → `validate_execute` (retry ×3 avec l'erreur) → `answer`.
Garde-fou `sqlglot` (SELECT unique, liste blanche de tables, fonctions de lecture de fichiers bloquées, `LIMIT` forcé), DuckDB sans accès externe, LLM via Ollama local.
Choix : LangGraph (pas CrewAI), Qdrant (pas ChromaDB), Streamlit puis React, **une installation = un client** (pas de multi-tenant), pas d'auto-modification non supervisée.
Modèles locaux à comparer **par l'éval** : Qwen2.5-Coder 32B, OmniSQL (vérifier la licence), DeepSeek en poids ouverts, modèles plus petits pour machines sans GPU.

---

## 3. Dashboards (rubrique clé : chaque personne et chaque société a ses propres templates)

### 3.1 Concepts
- **Dashboard** : document déclaratif versionné (`dashboard.yaml` / JSON) = titre, grille, filtres globaux, tuiles.
- **Tuile** : `{id, type: kpi|line|bar|table|pie|map, metric, dimensions, filters, options, source}` où `source` est soit une **métrique sémantique** (préférée), soit un **SQL épinglé** (issu d'une réponse validée).
- **Template** : dashboard dont les tuiles référencent des **emplacements abstraits** (`{{metric.chiffre_affaires}}`, `{{dim.date}}`) plus un **thème** (logo, couleurs, polices, langue). Il s'instancie sur le modèle sémantique d'un client en liant chaque emplacement à une vraie métrique/colonne.
- **Portées** : personnel → équipe → société → catalogue du produit. Chaque portée peut créer, dupliquer et partager ses templates.

### 3.2 Fonctionnalités
- **Épingler une réponse** du chat à un dashboard (le SQL validé et le graphique Plotly sont conservés).
- **Édition en langage naturel** (« ajoute un filtre par région », « passe en barres ») : le LLM produit un *diff* du `dashboard.yaml`, jamais du code ; l'utilisateur valide.
- Filtres globaux, drill-down, rafraîchissement planifié, export PDF/Excel/PNG.
- **Thème par société** (marque blanche pour revendeurs/intégrateurs).
- Import/export de templates en fichier (portabilité, partage entre clients d'un même intégrateur).
- **Liaison assistée** : à l'instanciation, le LLM *propose* l'appariement emplacement → métrique, un humain valide ; un template non résolu échoue explicitement (jamais de chiffre inventé).
- Sécurité : un dashboard n'exécute que des requêtes passant par `sql_guard` et les droits de l'utilisateur (RBAC au niveau base de données).
- Plus tard : intégration (iframe/URL signée), catalogue partagé entre clients.

### 3.3 Construire ou intégrer ?
- **Décision par défaut** : moteur léger maison (spec YAML + Plotly) pour garder la maîtrise de la souveraineté, de la couche sémantique et de l'expérience conversationnelle.
- **Point de décision au sprint 4** : évaluer Apache Superset (Apache 2.0, SDK d'embedding) comme moteur de dashboards optionnel selon : thèmes par client, import/export de templates, RLS, poids de maintenance. **Exclure Metabase** (AGPL ; white-label et embedding interactif payants).
- Palette, accessibilité et mise en page : suivre les guides de dataviz et de design du projet.

### 3.4 Critères de succès
- Un utilisateur crée un dashboard de 4 tuiles depuis un template en **moins de 5 minutes**.
- **3 templates de départ** (ventes, finance, opérations) fonctionnent sur **deux schémas de clients différents** après liaison.
- Aucune tuile ne contourne `sql_guard` (test automatisé).

---

## 4. Sprints

### Sprint 1 — Squelette et mesure ✅ (livré)
FastAPI, Ollama, DuckDB, `sql_guard`, pipeline 3 nœuds, harnais d'éval, tests (18 verts), Dockerfile et compose (non testés). **À faire par Claude Code** : lancer `python -m eval.run_eval` avec un vrai modèle Ollama et consigner le score de référence dans `eval/BASELINE.md`.

### Sprint 2 — Données réelles (2 sem.)
Connecteur PostgreSQL lecture seule (utilisateur DB dédié) ; Excel difficile (en-têtes, cellules fusionnées, feuilles multiples) ; jeu d'éval à **100 paires** (dont schémas larges, > 50 colonnes). **Succès** : 5 classeurs réels chargés correctement ; score mesuré sur schéma large.

### Sprint 3 — Couche sémantique (2 sem.)
Modèle sémantique YAML (glossaire, métriques, jointures, règles de désambiguïsation), éditeur admin simple, *schema linking* par embeddings locaux (bge-m3) + Qdrant. **Succès** : **+10 points** sur le jeu d'éval (la littérature indique +17 à +23 sur un cas favorable).

### Sprint 4 — Interface, confiance et dashboards v1 (3 sem.)
Streamlit : chat, dry-run (voir/éditer le SQL), Plotly, 👍/👎 + commentaire, journal d'audit. **Dashboards v1** : spec YAML, épingler une réponse, rendu, thème par société, sauvegarde de templates par portée. Décision Superset (3.3). **Succès** : un non-technicien pose 10 questions sans aide ; critères 3.4.

### Sprint 5 — Boucle d'amélioration supervisée (2 sem.)
Exemples validés (👍 + SQL confirmé) réinjectés en few-shot par similarité ; rapport hebdomadaire des erreurs récurrentes ; règles proposées puis **validées par un admin** ; versionnage et rollback. **Succès** : score en hausse sans régression sur le jeu fixe.

### Sprint 6 — Durcissement et pilote (2 sem.)
Réseau Docker interne + pare-feu hôte sortant, chiffrement disque documenté, RBAC minimal, export Excel/PDF, `THIRD_PARTY.md` et SBOM, tests d'injection de prompt (cellules, PDF) et d'exfiltration, déploiement chez un pilote. **Succès** : aucune connexion sortante sur 24 h ; `docker compose up` en une commande ; 1 pilote en usage réel.

### Sprint 7 — Connecteurs + RAG documentaire + Certificat de précision (livré)
Connecteurs MySQL (pymysql/MIT) et SQL Server (pymssql/LGPL-driver) via `POST /connectors/mysql|mssql` ; RAG documentaire PDF/DOCX (pypdf+python-docx) dans DuckDB FTS via `POST /documents/ingest` + `GET /documents/search`, injectable dans le prompt SQL ; certificat de précision `confidence` (score 0–1, label, explication) retourné par `/ask`. **Succès** : 332/332 tests verts.

### Sprint 8 — Templates liaison assistée + catalogue + intégration iframe (livré)
Wizard 3 étapes (métriques → dimensions → preview → confirm) via `/wizard/sessions/*` ; catalogue avec recherche, tags et notes (`/catalogue`) ; tokens d'embed HMAC-SHA256 signés ; routes `/embed/dashboard` et `/embed/ask` pour intégration iframe sans auth RBAC. **Succès** : 387/387 tests verts.

### Sprint 9 — Frontend React SPA (livré)
Vite + React + TypeScript dans `frontend/` ; pages Chat, Dashboards, Upload, Login ; composants ConfidenceBadge, SqlBlock, TileRenderer (recharts kpi/bar/line/table/pie), NavBar, ApiKeyGuard ; 17 tests Vitest + 4 tests Python ; FastAPI sert le build sur `/app/` si `frontend/dist/` existe. **Succès** : 391/391 tests Python, 17/17 Vitest.

### Sprints 10–22 (livrés)
PDF/DOCX avancé, multi-tenant, alertes, API versionnée v1, connecteurs Snowflake/BigQuery/MongoDB, conformité Loi 25/PIPEDA, tests E2E Playwright, cache performance, marketplace templates, onboarding guidé, certificat de précision, Helm chart + Prometheus/Grafana, productionisation hardening. **732 tests au total.**

### Sprint 23 — Extracteur universel de templates ✅ (2026-10-07)
Importation de templates depuis PDF, PNG/JPEG (OCR), Excel ou CSV : détection du secteur, extraction de KPI et sections, conversion en `DashboardTemplate` + tuiles (kpi/bar/pie/line/table), persistance JSON, routes `/user-templates` (extract/save/list/get/apply), RBAC viewer/editor. pypdf (MIT) remplace PyMuPDF (AGPL) pour rester conforme à la politique licences. **31 tests, 732/732 total.**

### Sprint H1 — Kimi K3 (fournisseur LLM OpenAI-compatible) ✅ (2026-10-14)
Pivot marché : Corne de l'Afrique, secteur humanitaire (INSTAD, OIM, UNHCR, IGAD). `KimiClient` OpenAI-compatible (`httpx`, aucune URL codée en dur), factory `get_llm_client()` (`LLM_PROVIDER=kimi|ollama`), avertissements startup. Latence CPU 4 min → ~5 s. 13 tests, 814/814 total.

### Sprint H2 — i18n Arabe / Anglais / Espagnol ✅ (2026-10-14)
Langues officielles du secteur humanitaire. `i18n.ts` (dictionnaires ar/en/es, ~60 clés), hook `useLocale` (LocaleContext, localStorage, `dir=rtl` sur `<html>` pour l'arabe), sélecteur de langue dans NavBar et LoginPage. Toutes les pages et composants traduits (ChatPage, UploadPage, DashboardPage, ConfidenceBadge, SqlBlock, TileRenderer). 20 tests i18n + locale completeness. 39/39 Vitest, 814/814 Python.

### Sprint H3 — Templates Corne de l'Afrique ✅ (2026-10-14)
3 YAML sectoriels (humanitarian, igad_economic, instad_census), registre `app/semantic/sectors.py`, parseur HXL `app/data/hxl_parser.py`, client HDX CKAN `app/data/hdx_client.py`, router `GET/POST /semantic/sectors`, 6 dashboard templates (3 humanitaires + 3 IGAD), 20 questions benchmark AR/EN/ES/FR (100%), 80 tests.

### Sprint H4 — Résilience terrain ✅ (2026-10-14)
`PersistentQueryCache` SQLite write-through (survie aux redémarrages, warm reload), `FallbackLLMClient` circuit-breaker Kimi→Ollama (3 échecs / 5 min), `POST /export/pdf-offline` (données directes, sans LLM), `POST /export/pdf-cached` (réponse depuis cache, 503 si absent). 33 tests.

---

## 5. Commercialisation (hypothèses à valider avec le pilote)
- Modèle : licence annuelle par installation + support/déploiement + options (templates sectoriels, connecteurs). Le code reste sous licence permissive ; la valeur est dans le produit, le support et la confiance.
- Cibles : PME et organisations soumises à la Loi 25, secteur public et parapublic canadien, cabinets et intégrateurs (marque blanche).
- Prérequis marketing : SBOM, politique de sécurité, preuve de non-sortie réseau, documentation FR/EN.
- Risques : précision sur bases réelles (Spider 2.0 : 10–20 %), coût du matériel GPU chez le client, concurrence de Wren AI (open core) et de Vanna.

## 6. Questions ouvertes
1. Quel modèle local atteint un score acceptable sur CPU seul ? (à trancher par l'éval)
2. Licences exactes des modèles candidats (OmniSQL, DeepSeek, Qwen) pour un usage commercial.
3. Superset ou moteur maison pour les dashboards (sprint 4).
4. Premier client pilote et secteur.

## Sources consultées
- Wren AI vs Vanna : https://getwren.ai/post/wren-ai-vs-vanna-the-enterprise-guide-to-choosing-a-text-to-sql-solution
- Dépôt Wren AI : https://github.com/Canner/WrenAI
- Spider 2.0 (synthèse) : https://ascii.co.uk/news/article/news-20260118-3e9e9dee/spider-20-exposes-text-to-sql-accuracy-crisis-in-enterprise
- Gemini-SQL2 / BIRD : https://aiweekly.co/alerts/googles-gemini-sql2-tops-bird-text-to-sql-at-8004
- OmniSQL : https://arxiv.org/pdf/2503.02240
- Couches sémantiques (arXiv) : https://arxiv.org/pdf/2604.25149
- dbt, couche sémantique vs text-to-SQL : https://docs.getdbt.com/blog/semantic-layer-vs-text-to-sql-2026
- Panorama analytique conversationnelle et prix : https://querio.ai/articles/conversational-analytics-tools-field-guide
- Prix Metabase : https://coefficient.io/metabase-pricing
- Cube : https://github.com/cube-js/cube — Superset : https://github.com/apache/superset
- DeepSeek V3.2 (licence, à recouper) : https://www.verdent.ai/guides/model/deepseek-v3-2
- Loi 25 : https://www.mccarthy.ca/fr/references/blogues/techlex/reforme-du-regime-de-protection-de-la-vie-privee-entre-en-vigueur-au-quebec

*Les chiffres de précision viennent de sources secondaires ou d'éditeurs ; ils servent d'ordres de grandeur, pas de promesses commerciales. Seul le harnais d'éval sur les données du client fait foi.*

# MizanBI — Plan de développement et de commercialisation

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
| Power BI Copilot | Intégré à Microsoft Fabric | Cloud | Pro ≈ 14 $ et Premium par utilisateur ≈ 24 $ par utilisateur/mois ; Copilot exige une capacité Fabric (F64 ≈ 5 000–8 400 $/mois selon la formule ; seuil contesté entre sources, nov. 2026) | Dépend du modèle sémantique existant, données dans le cloud Microsoft |
| Tableau Pulse | Digests de métriques automatisés | SaaS | n.d. | N'interroge que les données modélisées Tableau |
| Querio, Hex, Sigma, Omni, Looker+Gemini | Analytique conversationnelle moderne | SaaS | Querio ≈ 14 k$/an ; Hex 36–75 $/éditeur/mois | Cloud ; couche sémantique lourde (Looker) |
| **Wren AI** | BI générative **open core** : couche sémantique (MDL), RBAC, dashboards, 22+ sources | Cœur Apache 2.0 + parties AGPL-3.0 | Gratuit / commercial | Mis à jour nov. 2026 : l'interface de chat a été retirée (juin 2026), l'offre ouverte est une couche sémantique + CLI ; l'application complète (UI, tableaux de bord, gouvernance) est payante ; Ollama/vLLM annoncés (source éditeur). Moins un concurrent direct qu'une brique inspirante |
| **Vanna** (≈ 20 k étoiles) | Bibliothèque text-to-SQL par RAG | MIT | Gratuit | Pas de gouvernance, sémantique à curer à la main |
| Metabase | BI classique, IA en ajout | AGPL v3 ; white-label et embedding interactif **dès Pro (575 $/mois)** ; Enterprise ≈ 20 k$/an | Voir gauche | Licence contraignante pour la revente. Nov. 2026 : IA livrée dans la version ouverte (Metabase 60, avril 2026), clé de modèle fournie par l'utilisateur ; intégration du chat réservée aux offres payantes |
| Apache Superset | BI open source | **Apache 2.0**, SDK d'embedding | Gratuit | Pas conversationnel |
| Cube Core | Couche sémantique + API SQL/REST/GraphQL | Apache 2.0 / MIT | Gratuit | Contrôles d'accès avancés probablement commerciaux (à vérifier) |

Note : le comparatif de prix provient d'un blog éditeur (Querio) qui indique qu'aucun de ces outils n'offre d'auto-hébergement documenté. Power BI Report Server existe pourtant en on-premise, sans Copilot à ma connaissance : **à vérifier avant d'écrire « jamais offline » dans le marketing** (nov. 2026 : aucune source trouvée sur Copilot dans Report Server).

**Analyse détaillée (nov. 2026)** : voir `docs/benchmark-2026-11.md` (cinq familles d'équivalents, comparaison aspect par aspect avec Power BI, 16 idées dont l'ordre de priorité : mesures réutilisables + synonymes, métadonnées d'indicateurs + SDMX, abonnements par courriel + résumés automatiques, sécurité par ligne + jeux de données certifiés ; propositions P-065 à P-068 dans `docs/proposals.md`).

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

### Sprint H5 — Chatbot universel ✅ (2026-10-19)
`POST /api/v1/chatbot` : routeur intelligent SQL/général — détecte automatiquement si la question porte sur les données (`_DATA_PATTERNS`) ou sur un sujet général, historique de conversation (10 tours max), réponse unifiée `ChatResponse` (answer, mode, sql, columns, rows, confidence). `ChatPage.tsx` réécrite : bulles de conversation, badge mode data/général, SQL dépliable, case « Analyser les données ». 18 tests (12 Python + 6 seed). 945/945 tests.

### Livrables de mise en service ✅ (2026-11-15)
`docs/mise-en-service.md` (checklist vérifiable, contrôlée contre le code par un test), `docs/courrier-instad-validation.md` (brouillon, non envoyé), `.env.example` complété. Restent à faire par le propriétaire : décisions de la section 0 de la checklist, envoi du courrier, relectures de sécurité, juriste, restauration de sauvegarde testée, mesure de précision.

### Sprint H19 — P-071 Vérification d'intégrité du journal d'audit ✅ (2026-11-15)
`verify_audit_chain`, `GET /audit/verify` (admin, méta-audité), `tools/verify_audit.py`, ancrage externe (`entries` + `head`), 32 tests dont les limites verrouillées, DPA/procédure d'incident/sécurité corrigés. **Limite** : chaîne non signée (HMAC = migration à décider). 1847 pytest.

### Sprint H18 — P-070 Mode strict de l'IA ✅ (2026-11-15)
`SOVEREIGN_AI_STRICT=1` : schéma + question seulement vers le modèle (plus d'exemples de lignes, résultats, extraits de documents, insights, réponses d'historique, valeurs d'erreurs) ; réponse locale ; avis de confidentialité, DPA et avertissement de démarrage. 22 tests, 1785 pytest. **Décision du propriétaire : actif par défaut avec un LLM externe** (automatique selon `LLM_PROVIDER`, `SOVEREIGN_AI_STRICT=0` pour désactiver, avertissement au démarrage), 1798 pytest. **Outil `eval.compare_strict` livré (12 tests), mesure toujours à faire** (modèle visé requis) ; prévenir le pilote Djibouti du changement de réponses. **Pastille du mode IA dans l'en-tête livrée (3 états vérifiés en navigateur, 429 Vitest).** **Annexe D du DPA (fournisseur d'IA) livrée** avec test de cohérence DPA/code ; P-071 (vérification du journal d'audit) proposée.

### Sprint H17 — P-069 Jeux de données certifiés ✅ API (2026-11-15)
Registre signé de validations institutionnelles par table, empreinte du contenu (pastille « modifiée depuis la certification » automatique), révocation, expiration, détection d'altération du registre. 1763 pytest. Pastille sur l'accueil et écran admin de validation/révocation dans le client, vérifiés en navigateur réel (19 tests Vitest, 382 au total). **Reste** : pastille dans chat/tuiles/bulletins ; confirmation écrite de l'INSTAD avant tout usage du mot « certifié ».

### Sprint H16 — P-068 Sécurité par ligne ✅ (2026-11-15)
Règles table/colonne/périmètre, réécriture SQL à un seul point d'étranglement (`DataStore.execute`), identité par middleware, périmètres par compte, échec fermé (clés API viewer/editor, planificateur, courriels, jetons de partage refusés), caches partagés coupés, diagnostic admin. Relue par `security-reviewer` (aucun contournement ; 7 constats corrigés). 1743 pytest. **Reste** : relecture du propriétaire ; P-069 (jeux de données certifiés) en attente d'accord.

### Sprint H15 — P-064 Vie privée opérationnelle ✅ volet technique (2026-11-15)
Export et suppression de compte (admin, confirmation par e-mail, dernier admin protégé), registre d'incidents avec alerte 72 h, DPA brouillon + procédure d'incident. 1698 pytest. **Reste** : juriste, version anglaise, relecture sécurité d'`erase_account`. P-068 (sécurité par ligne) : constat fait, décisions de conception demandées.

### Sprint H14 — P-067 Abonnements courriel ✅ (2026-11-15) — écran de gestion ajouté au client le même jour (407 Vitest) ; correctif de la sous-navigation qui masquait la barre d'outils des tableaux de bord
Abonnements quotidiens/hebdomadaires/mensuels à un bulletin de tableau de bord, envoi planifié (échéance calculée, une tentative par échéance), SMTP STARTTLS ou boîte d'envoi locale, désabonnement par jeton HMAC (GET formulaire, POST suppression). 1683 pytest. **Limites** : non testé contre un vrai SMTP, pas de double opt-in, pas d'interface, une seule instance. En attente d'accord : P-064, P-068.

### Sprint H13 — P-066 Métadonnées d'indicateurs et SDMX-CSV ✅ (2026-11-15) — boutons d'export « ↓ SDMX » et d'import SDMX-CSV (vérifier puis charger) ajoutés au client le même jour (418 Vitest)
Métadonnées d'indicateur sur les mesures (code, source, périodicité SDMX, définition, méthodologie, thème, mise à jour) validées et exposées (`GET /semantic/indicators`) ; `app/sdmx/csv_format.py` (SDMX-CSV 2.0 écriture/lecture, périodes SDMX, anti-injection de formules) ; export SDMX-CSV d'une tuile ; `POST /sdmx/import` (éditeur, préfixe `sdmx_` forcé). 1655 pytest. **Limites** : pas de SDMX-ML ni d'API REST SDMX, pas de DSD/codelists réelles, non validé avec un registre SDMX officiel, bouton d'export ajouté ensuite (pas d'import dans le client). Proposées en attente d'accord : P-064, P-067, P-068.

### Sprint H21 — P-073 Moteur de formules financières versionnées ✅ (2026-11-18)
Premier module du pack Audit (P-073 à P-077, en attente d'accord pour la suite). `app/financial/` (évaluateur sans `eval`, registre YAML versionné, moteur Decimal, historique des analyses), routes `/financial/*`, 11 formules v1, liaison `formula:` dans la couche sémantique. Relecture sécurité : 7 constats sur 8 corrigés (historique protégé de l'upload et de la lecture croisée, entrées bornées, audit avant écriture). Limite : le chat n'appelle pas encore le moteur. 1990 pytest verts. Doc : `docs/formules-financieres.md`.

### Sprint H20 — P-072 Carte imprimable Djibouti-ville + couverture CERD ✅ (2026-11-18)
PDF A3 (vue d'ensemble + une carte par commune) via `tools/make_djibouti_ville_map.py` ; deux jeux CERD distingués (levé topographique = 3 communes ; couches anciennes = Balbala seulement), note UI/catalogue/CLAUDE.md corrigés, tests de couverture pytest + Vitest. 1859 pytest · 430 Vitest.

### Sprint H12 — P-065 Couche sémantique : mesures, filtres et synonymes ✅ (2026-11-15)
Résolveur déterministe de termes métier (`app/semantic/resolver.py`), validateur de modèle (`app/semantic/validate.py`), modèle étendu (filtres nommés, synonymes de valeurs et de colonnes, unités), routes `GET /semantic/validate|resolve`. **Deux défauts corrigés** : le LLM ne recevait ni mesures, ni tables, ni jointures du modèle v2 (seulement glossaire et règles) ; un secteur activé injectait la représentation Python de l'objet. 1595 pytest. **Gain de précision non mesuré** (pas de modèle de génération local) : à établir avec le harnais d'éval, ce qui reste la ligne de base jamais produite (`eval/BASELINE.md`). Prochaines propositions en attente d'accord : P-064 (DPA), P-066 (SDMX), P-067 (abonnements courriel), P-068 (sécurité par ligne).

### Sprint H11 — Cartographie officielle Djibouti-ville, juridique, durcissement web ✅ (2026-11-14/15)
**P-057** découpage officiel CERD `admin_pol` (91 quartiers, 3 communes, ITRF2005→WGS84, `.shx` régénéré) · **P-058** routes OSM du centre · **P-059** attribution automatique des sources (`catalog.yaml` → `tools/sync_geo_attribution.py` → `GeoSources`) · **P-060** `MapAdm2` sur les quartiers officiels · **P-061** documents juridiques fr/en (confidentialité, CGU, cookies, mentions légales, config unique `legalConfig.ts`, fenêtre d'acceptation + `POST /compliance/consent/self`, glyphes de cartes hébergés localement) · **P-062** durcissement web (clé API retirée du navigateur, analytics après consentement, `noindex`, PNG Open Graph, favicons, vrai 404, pages en `React.lazy` : entrée 3,8 Mo → 281 Ko) + `tools/web_launch_audit.py` réutilisable · **P-063** levé topographique CERD 1/2 500 (86 776 bâtiments typés, routes, hydro, rail, sites ; gzip servi à la demande, rendu canvas par lots, mer en fond uniforme). 1562 pytest + 363 Vitest. Projets voisins traités avec le même outil d'audit : Code de la Route DJ (pages légales, SEO, 404, route `/verify` réparée) et Loiyale (ex-Vigile, Loi 25/PIPEDA, dépôt privé `robkira01-max/loiyale`, en ligne sur `loiyale.vercel.app`).
**Reste (propriétaire)** : compléter `legalConfig.ts` + validation juridique + `draft:false` · licences CERD par écrit · DPA type, procédure d'incident, outil d'export/suppression de données (P-064 à proposer) · intégrer au besoin `centre_lin`, `contour`, `road_lin`, `utilit_*`, `vegetation` du levé · rebuild Oracle avec `VITE_API_BASE` et `VITE_SITE_URL` · `LLM_PROVIDER` · relecture humaine de `app/auth/` et de `/compliance/consent/self`.

### Sprint H10 — P-024 Import GeoJSON/GeoPackage/GeoParquet ✅ (2026-11-08)
Pipeline d'import géographique : `app/geo_catalog/importer.py` (validation DuckDB Spatial, extraction feature_count/geometry_type/bbox/name_col, sanitisation nom, enregistrement catalog.yaml en status:draft). `POST /api/v1/geo/import` (multipart, editor-only, 50 Mo, extension allowlist, guard path traversal). `GeoImport.tsx` drag-and-drop + champs métadonnées + callback `onImported`. i18n `geo_import.*` 4 locales (fr/en/ar/es). Fixture `monkeypatch` pour isolation tests (catalog.yaml non pollué). 1225/1227 pytest · 124/124 Vitest.

### Sprint H9 — P-023 Moteur d'analyse spatiale DuckDB Spatial ✅ (2026-11-08)
SpatialEngine DuckDB 1.5.6 : 5 analyses (area/centroid/bbox/nearest/summary), `ST_Area_Spheroid`, `ST_Distance`, path guard projet root. `file_path`+`name_column` dans catalog.yaml. `GET /api/v1/geo/analyze/types`, `POST /api/v1/geo/analyze`. 23 pytest. 1201/1203 tests.

### Sprint H9 — P-052 Tiles avancées + P-053 Exports JS + P-055 Nettoyage frontend ✅ (2026-11-11)
Langue arabe supprimée (`Lang = 'fr' | 'en'`, ~175 lignes retirées de `i18n.ts`, `SIG_LANGS` supprimé, `dirOf` simplifié). P-053 exports pur client : `lib/exports.ts` (`tileDataToCsv`, `dashboardToBulletinHtml`, `triggerDownload`), `DemoDashboardDetail` sans appel API, bouton CSV par tuile (si `tile.data` présent). `Tile.data?: TileData` ajouté à l'interface API. P-055 : `frontend/` supprimé (74 fichiers, `git rm -r`), service `mizanbi-client` activé dans `docker-compose.server.yml`. Q-002 et Q-003 fermées dans `docs/questions.md`. 257/257 Vitest · `tsc --noEmit` propre · `vite build` propre. Commits : `b0cb391` (P-053), `5cb2627` (P-055).

### Sprint H8 — P-022 Catalogue géospatial MizanGeo + HeatmapTile ✅ (2026-11-08)
Pivot stratégique : MizanBI → MizanBI + MizanGeo + MizanAI (socle commun). Catalogue géospatial centralisé (`data/geo/catalog.yaml`, `app/geo_catalog/`, `GET|PUT /api/v1/geo/catalog`), 3 couches DJ référencées (ADM1 CC BY 4.0, ADM2 CC BY 4.0, quartiers ODbL draft+avertissement). `GeoCatalog.tsx` (viewer/editor, toggle, badges statut, avertissements qualité, filtre enabled_only). HeatmapTile SVG 1D/2D 4 palettes. Feuille de route P-023→P-029 ajoutée dans proposals.md. 1178/1180 tests (2 pre-existing) · 114/114 Vitest.

### Sprint H7 — Propositions P-017 à P-021 ✅ (2026-11-07)
Annotations tuiles (`Tile.note`, `PUT .../note`, 1 000 chars max) · Tri + filtrage inline des tables (`TableTile.tsx`) · Étiquettes dashboards (`Dashboard.tags`, `PUT .../tags`, filtre `GET ?tag=`) · Connecteur UN Comtrade Plus v1 (`ComtradeClient`, fallback démo, `tools/ingest_comtrade.py`) · Choroplèthe ADM2 + Quartiers Djibouti-ville (`MapAdm2.tsx`, `GET /api/v1/geo/dj/{adm1|adm2|quartiers}`, 11 quartiers OSM approximatifs, `tools/download_dj_geo.py`). 1151/1153 tests (2 pre-existing) · 93/93 Vitest.

### Sprint H6 — Seed INSTAD et infrastructure Hetzner ✅ (2026-10-19)
`SOVEREIGN_SEED_DIR` : chargement automatique de CSV/XLSX au démarrage FastAPI (lifespan), 7 tables INSTAD pilote persistées dans un volume Docker (`sovereign_uploads`). `tools/setup-oracle-server.sh` : bootstrap Oracle Cloud Ubuntu 22.04 ARM en une commande (Docker, iptables, git clone, génération `.env`, build+up). Déploiement Hetzner : `docker-compose.hetzner.yml` sur `46.225.233.135`, réseau partagé `lexbouti_default` (Ollama + Caddy mutualisés), HTTPS `bi.46-225-233-135.nip.io` via nip.io. Fix routing SPA : route catch-all `GET /app/{path:path}` remplace `StaticFiles(html=True)` (qui ne servait `index.html` que pour les répertoires). Fix navigation frontend : `vite.config.ts` `base='/app/'`, tous les liens et redirects utilisent `import.meta.env.BASE_URL`. 945/945 tests.

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

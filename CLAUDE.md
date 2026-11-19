# MizanBI — consignes pour Claude Code

Lis `PLAN.md` en entier avant toute action : c'est la source de vérité (benchmark, dashboards, sprints, politique DeepSeek).

## Protocole de session

1. **Début de session** : lire ce fichier + `PLAN.md`, identifier la dernière proposition livrée dans `docs/proposals.md`, reprendre à la suivante.
2. **Exécution** : backend + tests pytest → frontend + Vitest → `py_compile` → commit. Pas d'étape sautée.
3. **Fin de session** : mettre à jour `docs/proposals.md` (cocher ✅), `PLAN.md` (ajouter sprint/note), et ce fichier (`CLAUDE.md`). Résumé en six points (voir ci-dessous).
4. **Hors plan** : proposer dans `docs/proposals.md` avec raison + impact. Ne jamais implémenter sans accord.
5. **Fin de session — résumé obligatoire** :
   - ✅ Fait (P-XXX avec note)
   - ⏭ Prochaine tâche
   - 🔴 Bloqué
   - ❓ Décisions en attente
   - 📝 À retenir (env vars à setter, migrations, etc.)
   - 📋 Nouvelles proposals ajoutées

## Règles techniques

- **Tests** : `pytest` depuis la racine avec `.venv/bin/python` (Python 3.14 système n'a pas duckdb). Suite verte, aucun échec toléré. Un test qui modifie `app.state.store` doit passer par `monkeypatch.setattr` (jamais d'affectation directe : elle fuit vers les tests suivants).
- **Auth** : rôle par utilisateur (`users.role` : viewer|editor|admin, défaut viewer) ; tout accès Bearer passe par `RequireRole`. Les nouvelles routes doivent déclarer une dépendance `RequireRole` (aucune route de mutation publique). `X-Forwarded-For` n'est lu que depuis `SOVEREIGN_TRUSTED_PROXIES` (défaut `private` ; `none` si le port est publié sans proxy). Sessions stockées hachées (SHA-256).
- **Vitest** : `cd frontend && npx vitest run`. `vi.mock()` factory : ne jamais référencer de variables module-level (hoisté avant initialisation) — inliner les données.
- **py_compile** : valider chaque fichier Python avant commit.
- **External URLs** dans `app/` : toute nouvelle URL base doit être ajoutée au lookahead regex de `tests/test_network_isolation.py`.
- **DeepSeek** : dev uniquement, données synthétiques, via `tools/dev_llm.py`. `app/` n'importe jamais `tools/`.
- **Licences** : MIT/Apache/BSD uniquement ; tenir `THIRD_PARTY.md` à jour.
- **Code** : anglais. **UI + docs** : français (anglais second).

## État courant (2026-11-18)

- **Tests** : 2308 pytest + 466 Vitest mizanbi-client (2026-11-19, après P-079 et couches JICA) · `tsc --noEmit` propre (mizanbi-client) · `ruff check .` : 66 erreurs **préexistantes** (surtout E702 dans d'anciens `tools/`), aucune dans les fichiers de la session du 2026-11-18
- **Durcissement web (P-062)** : pas de clé API dans le navigateur (`window.__MIZAN_API_KEY__` supprimé, auth par session uniquement) ; mesure d'audience (`lib/analytics.ts`) chargée seulement après consentement ; l'application est `noindex` (balise + `X-Robots-Tag`) sans `Disallow` dans robots.txt (sinon pas d'aperçus LinkedIn/Facebook) et sans sitemap ; OG en PNG 1200×630 + favicons/icônes générés par `tools/make_brand_assets.py` ; `VITE_SITE_URL` rend absolues les URL OG au build ; titre d'onglet par écran (`lib/pageTitle.ts`) ; `nginx.conf` renvoie un vrai 404 (`public/404.html`) ; pages en `React.lazy` (entrée 3,8 Mo → 281 Ko).
- **Audit web réutilisable** : `python3 tools/web_launch_audit.py <url> [--json] [--fail-on warn]` (stdlib seule, copiable dans tout projet ; vérifie HTTPS/HSTS, en-têtes, title/description, OG, favicons, robots/sitemap, soft-404, alt, contenu mixte, tiers, liens, poids). Ne lit que le HTML servi : les SPA, Core Web Vitals, contraste et clavier restent à vérifier avec Lighthouse/Playwright. Résultat MizanBI (nginx réel) : 18 PASS / 0 WARN / 0 FAIL.
- **Documents juridiques (P-061)** : confidentialité, CGU, cookies, mentions légales (fr/en) dans `mizanbi-client/src/lib/legalContent.ts`, valeurs propres à l'éditeur dans `legalConfig.ts` (UN seul endroit : placeholders `[À COMPLÉTER : …]` surlignés tant que `draft: true`). Accessibles avant connexion (liens sur le login). Fenêtre d'acceptation `TermsGate` (version `LEGAL.version`, enregistrée via `POST /compliance/consent/self`, identité tirée de la session). Quand les placeholders sont remplis et le texte validé par un juriste : `draft: false` (un test échoue s'il reste un placeholder). Les tests vérifient aussi que chaque clé de stockage local du code est documentée dans la page cookies et qu'aucun service tiers n'est chargé. Polices de cartes hébergées localement (`public/fonts/`, Apache 2.0).
- **Attribution auto des cartes** : `data/geo/catalog.yaml` = source de vérité → `tools/sync_geo_attribution.py` génère `mizanbi-client/src/data/geo_attribution.json` (ne pas éditer à la main) → composant `GeoSources` (pieds de carte SIG). À relancer après tout changement du catalogue ; `tests/test_geo_attribution_sync.py` échoue si désynchronisé.
- **Levé topographique CERD à la demande (P-063)** : `tools/convert_cerd_topo.py <dossier_shp>` convertit le levé photogrammétrique 1/2 500 (2014, fourni par le propriétaire en `ESRI_Shapefile_ok.zip`) en `data/geo/cerd_{batiments,routes,hydro,rail,sites}.geojson.gz` (86 776 bâtiments ≥ 12 m² classés par usage, 1 155 routes, 1 554 entités hydro, 201 tronçons de voie ferrée, 1 408 sites ; ~2,7 Mo gz au total) servis pré-compressés par `/api/v1/geo/dj/{id}` ; `DjiboutiVilleMap` les charge au cochage (`lib/topoLayers.ts`, `TopoCanvas` canvas — des dizaines de milliers de nœuds SVG figeraient le navigateur). Remplace l'ancienne couche OSM des bâtiments (supprimée). En mode démo (VITE_API_BASE vide) : message « nécessite l'API ». Couches du zip non intégrées : curves de niveau (`contour`, 19 Mo), axes de routes (`centre_lin`, 25 642), trottoirs/sentiers (`road_lin`), réseaux (`utilit_*`), `vegetation` — à demander si besoin.
- **Dernière proposal** : P-080 chat branché sur le moteur de formules — 2026-11-19 (livré ; P-079 : acceptation = session d'essai avec un auditeur, puis P-076/P-077). P-057 à P-075 livrés ; P-076 à P-078 en attente d'accord, voir `docs/proposals.md`). P-054 était déjà livré (2026-11-13)
- **Carte imprimable (P-072)** : `.venv/bin/python tools/make_djibouti_ville_map.py [sortie.pdf] [--commune Balbala|Boulaos|Ras-Dika] [--no-licence-warning]` → PDF A3 paysage (communes, 91 quartiers, bâtiments par usage, routes, hydro, rail, échelle, légende, sources). Lit seulement `data/geo/`, aucun réseau. La ligne rouge « licence CERD non confirmée » est ajoutée par défaut : ne la retirer que si la licence est confirmée par écrit. Test de couverture : `tests/test_geo_cerd_coverage.py` + test Vitest `djibouti_ville_map.test.ts` (échouent volontairement si des données CERD arrivent pour le centre : mettre à jour note UI, `catalog.yaml` et item (5) ci-dessous)
- **mizanbi-client** : `mizanbi-client/` — frontend standalone React (recharts, pdfjs, StatCan/BIE/BCD), `npm test` / `npm run build` depuis `mizanbi-client/`
- **Commit** : tout est sur `master` ; poussé jusqu'à `d86318a` (P-079). P-080 (`4214eef`) et P-082 ne sont pas poussés.
- **CI GitHub Actions** : `.github/workflows/ci.yml` — lint + pytest + tsc + vitest + vite build + docker smoke, déclenché sur `master`
- **Dockerfile + nginx.conf** : `mizanbi-client/Dockerfile` + `mizanbi-client/nginx.conf` — build nginx:alpine, SPA fallback, security headers
- **Langue arabe supprimée** : `Lang = 'fr' | 'en'`, dictionnaire ar retiré, SIG_LANGS supprimé, dirOf simplifié
- **Frontend unique** : `mizanbi-client/` — `frontend/` supprimé (P-055, 2026-11-11), service Docker activé dans `docker-compose.server.yml`
- **Cartographie pro** : `tools/make_pro_maps.py` — cartes print-quality (cartopy + mapclassify + contextily) : population choroplèthe ADM1 (Fisher-Jenks), accès aux soins, Djibouti-ville communes+quartiers (CartoDB Positron z=15). Librairies installées dans le venv : `cartopy==0.26.0 mapclassify==2.11.0 contextily==1.7.1`.
- **Reprise** — décisions propriétaire restantes :
  - (1) relecture humaine de `app/auth/` (règle Sécurité, voir `docs/auth-review.md`)
  - (2) setter `LLM_PROVIDER` sur Oracle (vide → IA silencieuse)
  - (3) rebuild image Oracle : `docker compose -f docker-compose.server.yml build mizanbi-client && docker compose -f docker-compose.server.yml up -d`
  - (4) ✅ résolu 2026-11-14 : découpage officiel `admin_pol.shp` fourni par le **CERD** (photogrammétrie 1/2 500, 2014, même licence que les autres couches CERD) → `data/geo/admin_quartiers.geojson` (91 quartiers) + `admin_communes.geojson` (3 communes dissoutes), routes `/api/v1/geo/dj/admin_quartiers|admin_communes`, fond `VilleBaseLayers` ; `.shx` manquant régénéré via SHAPE_RESTORE_SHX. **De nouvelles données CERD sont attendues prochainement** (propriétaire, 2026-11-14) : réutiliser le même pipeline (latin-1, reprojection WGS84, catalog.yaml, tests)
  - (5) précisé 2026-11-18 — **deux jeux CERD à ne pas confondre** (mesuré par comptage par commune) : (a) **levé topographique** (P-063 : `cerd_batiments/routes/hydro/rail/sites`) = **3 communes, centre compris** (bâtiments Balbala 56 198 / Boulaos 26 203 / Ras-Dika 3 829 ; routes 666 / 387 / 85 ; voie ferrée 0 / 49 / 129 ; lon 43.03–43.19) ; (b) **couches CERD anciennes** (`cerd_voirie`, `cerd_ilots`, `cerd_equipements_sociaux/scolaires`, `cerd_secteurs_adressage`, `cerd_typologies_urbaines`, `cerd_lignes_bus`, `cerd_terminus_bus`, `cerd_communes`) = **Balbala seulement** (arr. 4 et 5, lon 43.06–43.14 ; ex. voirie 1 435/1 447 à Balbala, équipements scolaires 31/31) : demander au CERD/Mairie le même jeu pour le centre (arr. 1–3), surtout équipements, écoles, secteurs, typologies. Pour la voirie du centre, `DjiboutiVilleMap` garde la couche OSM (cochée par défaut, `centre: true`) en plus des « Routes (CERD 2014) » du levé topographique ; la décocher par défaut est à décider. OSM (ODbL, Geofabrik 2026-11-14) : `osm_centre_voirie.json` (1875 tronçons, lon 43.125–43.185 / lat 11.53–11.625, aéroport inclus) + `osm_centre_lieux.json` (30 quartiers), couche `osm_centre_voirie` dans `catalog.yaml`. Les cartes santé/écoles « Djibouti-ville » (`StructuresSanteMap`, `EcolesMap`, `CerdEcolesMap`) utilisent ce même fond via `VilleBaseLayers` + `lib/villeGeo.ts` ; `getQuartierForPoint` utilise les 91 quartiers officiels admin_pol et `dj-quartiers.json` (11 rectangles OSM) ne sert plus qu'à la couche catalogue `dj_quartiers`. `osm_centre_lieux.json` supprimé (remplacé par les libellés admin_pol).
  - (6) juridique : compléter `mizanbi-client/src/lib/legalConfig.ts` (entité, contacts, hébergeur, fournisseur d'IA, droit applicable, conservation), faire valider par un juriste, puis `draft: false` ; préparer un DPA pour banques/ONG/administrations (rôles responsable/sous-traitant, sous-traitants, transferts, incidents)
  - (7) web : `VITE_SITE_URL` (URL publique, aperçus de partage) + `VITE_API_BASE` au build du client ; HSTS/redirection HTTPS côté serveur de production ; Lighthouse sur l'URL publique
  - (8) levé CERD : licence par écrit ; couches du zip non intégrées (`centre_lin`, `contour`, `road_lin`, `utilit_*`, `vegetation`) ; l'archive `ESRI_Shapefile_ok.zip` (859 Mo) peut être supprimée du disque
- **Couche sémantique (P-065)** : `app/semantic/{model,resolver,validate}.py` ; le pipeline reçoit le texte complet du modèle (`get_graph` → `model_to_prompt_text`) plus les termes reconnus dans la question (mesures, filtres nommés, synonymes de valeurs et de colonnes). `GET /semantic/validate` contrôle le modèle actif, `GET /semantic/resolve?q=` montre les termes reconnus. Ajouter une mesure/un synonyme = éditer `semantic/model.yaml` puis `validate`. **Gain de précision non mesuré** (aucun modèle de génération local) : mesurer avec `python -m eval.run_eval` sur machine avec modèle avant de l'annoncer.
- **SDMX et indicateurs (P-066)** : `app/sdmx/csv_format.py` (SDMX-CSV 2.0, lecture 1.0 aussi, **pas de SDMX-ML**) ; `GET /dashboards/{id}/tiles/{id}/export/sdmx-csv` ; `POST /sdmx/import` (éditeur, tables `sdmx_*` à préfixe forcé, `dry_run`) ; métadonnées d'indicateur sur les mesures (`code`, `frequency` SDMX, `source`, `definition`…) et `GET /semantic/indicators`. Agence SDMX par défaut `MIZANBI` à remplacer ; fichier non validé avec un registre SDMX officiel. Bouton « ↓ SDMX » sur chaque tuile (`SdmxExportButton`) et carte « Import SDMX-CSV » sur la page Import (`SdmxImport`, vérifier puis charger), vérifiés en navigateur.
- **Abonnements courriel (P-067)** (écran client : bouton « ✉ Abonnements » sur un tableau de bord, éditeur/admin, vérifié en navigateur) : `app/subscriptions/{store,mailer,service}.py`, `app/routers/subscriptions.py` ; tâche planifiée dans `lifespan` (`SOVEREIGN_SUBSCRIPTIONS=0` la coupe). **Sans `SMTP_HOST`, aucun courriel réel** (boîte d'envoi `data/outbox/`). À setter pour envoyer : `SMTP_HOST/PORT/USER/PASSWORD/FROM`, `SOVEREIGN_PUBLIC_URL` (https), optionnel `SOVEREIGN_SUBSCRIPTION_DOMAINS`. Jamais testé contre un vrai SMTP ; pas de double opt-in.
- **Vie privée opérationnelle (P-064)** : export/suppression de compte et registre d'incidents (admin) ; `docs/legal/dpa-fr.md` (BROUILLON non validé, `[À COMPLÉTER]`) et `docs/incident-procedure.md`. `erase_account` attend la relecture `security-reviewer` + propriétaire. 
- **Sécurité par ligne (P-068)** : `app/security/row_policy.py` + `principal_mw.py` ; règles dans `data/row_policies.yaml` (exemple : `data/row_policies.example.yaml`), périmètres par compte via `PUT /security/users/{id}/scopes/{scope}` (admin). **Échec fermé** : sans périmètre, clé API viewer/editor, planificateur, courriel, jeton de partage = refus sur les tables protégées ; admin voit tout ; fichier mal formé ou chemin explicite introuvable = refus (jamais « sans protection »). Toute lecture DuckDB passe par `DataStore.execute` : **ne jamais utiliser `store.con.execute` pour des lignes** (contourne la sécurité). Caches partagés coupés quand des règles existent. Relue par `security-reviewer` (7 constats corrigés) ; **relecture du propriétaire due**.
- **Jeux de données certifiés (P-069)** : `app/certification/registry.py`, `/certification` ; l'admin enregistre « validé par X » + référence ; empreinte du contenu → pastille `stale` dès que les données changent ; HMAC (`SOVEREIGN_CERT_SECRET`, obligatoire en production). **MizanBI ne vérifie pas l'institution** : ne pas annoncer « certifié INSTAD » sans confirmation écrite de l'INSTAD. Pastille sur l'accueil (`CertificationBadge`) et écran admin de validation/révocation (`CertificationAdmin`, dans Paramètres › Comptes), vérifiés en navigateur ; pas encore dans le chat/tuiles/bulletins.
- **Mode strict de l'IA (P-070)** : **actif par défaut dès que `LLM_PROVIDER` n'est pas `ollama`** (décision du propriétaire 2026-11-15) ; `SOVEREIGN_AI_STRICT=1` force, `=0` désactive (avertissement au démarrage). Plus aucune ligne de données, résultat, extrait de document ni insight envoyés au modèle (schéma + question seulement) ; réponses rédigées localement. Effet pour un déploiement kimi existant : réponses « N lignes (colonnes : …) », insights IA absents, précision SQL non mesurée. Mesure de précision strict/ouvert : `python -m eval.compare_strict` (outil prêt, **aucune mesure exploitable à ce jour** : exige le modèle visé). Pastille « IA locale / externe · strict / externe · non strict » dans l'en-tête (`AiModeBadge`, via `/compliance/notice`). Toute nouvelle fonction qui envoie du contenu au LLM doit respecter `ai_policy.strict()` (voir `docs/securite.md`).
- **Intégrité du journal d'audit (P-071)** : `GET /audit/verify` (admin) et `python tools/verify_audit.py` ; **ancrer** (`entries` + `head` notés hors du serveur) pour détecter une troncature ; la chaîne n'est pas signée par un secret (une réécriture complète par quelqu'un qui contrôle le serveur reste possible).
- **Formules financières (P-073, pack Audit)** : `app/financial/` + `app/routers/financial.py` + `rules/financial/*.yaml` (11 formules v1), doc d'usage `docs/formules-financieres.md`. Règles : modifier une formule = AJOUTER une version (jamais éditer l'ancienne : `definition_status: definition_changed`) ; calcul en Decimal, montants en chaînes ; erreurs explicites (422), jamais de 0/NaN silencieux. **`audit_analysis_runs` et `audit_calculation_results` sont des noms réservés** (`RESERVED_TABLES` dans `duckdb_store.py` : upload refusé, exclues de `store.tables`, donc invisibles de l'IA) ; ne pas les lire autrement que par `app/financial/runs.py`. Un run issu d'une table n'est lisible que par son auteur et l'admin (sinon contournement de la sécurité par ligne). `rules/` doit rester dans `COPY` des Dockerfiles (un test le vérifie ; `Dockerfile` est en lecture seule : `chmod u+w` puis `u-w`). **Non fait** : le chat n'appelle pas le moteur (une mesure peut pointer vers une formule via `formula:`, mais le text-to-SQL génère toujours son SQL : chiffre du chat = exploratoire), pastille P-069 non branchée, `result_hash` non signé. Relu `security-reviewer` : 8 constats, 7 corrigés (F2 laissé).
- **Import d'audit (P-074, pack Audit)** : `app/audit_data/` + `app/routers/audit_data.py` ; originaux dans `SOVEREIGN_AUDIT_DOCS_DIR` (défaut `data/audit_docs/`, gitignoré, nommés par SHA-256, 0400). `audit_documents` et `audit_quality_issues` sont des noms **réservés** (invisibles de l'IA) ; `audit_financial_records` est interrogeable mais non remplaçable par upload. Séparateur décimal et format de date sont toujours déclarés par l'utilisateur ; devise obligatoire. Quand des règles de sécurité par ligne existent, aperçu/anomalies/résumés sont réservés à l'admin. **À faire par le propriétaire** : ajouter `defusedxml>=0.7` à `pyproject.toml` (lecture seule) et `request_body max_size` dans Caddy ; chiffrer le volume des originaux en production.
- **Couches JICA (SIG)** : 30 couches (5 thèmes) dans `data/geo/jica/*.geojson.gz`, générées par `tools/convert_jica_rdd.py` et `tools/convert_jica_all.py`, routes pilotées par le catalogue. **Licence JICA non confirmée**, noms/classes provisoires (en attente du retour JICA), projection UTM 38N supposée pour les couches sans .prj ; rien n'est publié (usage interne/entraînement). Source = JICA, pas CERD.
- **Interface pack Audit (P-079)** : `mizanbi-client/src/pages/{AuditData,AuditRules,Financial}.tsx`, `lib/auditApi.ts`, `components/audit/common.tsx`, section `audit` de `i18n.ts`. Montants toujours en chaînes (`formatDecimal`) ; vocabulaire « signal de risque » ; pas de nouvelle clé de stockage local. **Session d'essai avec un auditeur à faire** avant P-076/P-077.
- **Exports tabulaires (P-082)** : tout export CSV/Excel passe par `app/export/sanitize.py` (`neutralize_cell`) ; `tests/test_export_sanitize.py` échoue si un module écrit un CSV/classeur sans l'importer. Les nombres restent des nombres, seuls les textes sont préfixés d'une apostrophe.
- **Identité (P-083)** : `RequireRole` (async) pose `current_identity` (session | clé personnelle `mzb_` | clé héritée) lu par `record_audit` ; `RequireRole(..., session_only=True)` pour résolution/revue/validation ; clés héritées : `app/security/legacy_keys.py` (échéance, lecture seule en production). Tout module qui écrit une table doit figurer dans `ALLOWED_WRITERS` (`tests/test_api_keys.py`). Relecture humaine de `app/auth/` en attente.
- **Chat et formules (P-080)** : `app/pipeline/formula_route.py` (déterministe, aucun LLM, une seule fonction autorisée `perform_run` de `app/financial/service.py`). Une mesure sémantique avec `formula:` + `formula_inputs:` (variable → table.colonne) est calculée par le moteur ; sinon réponse `provenance: exploratory`. Paramètres jamais devinés ni lus dans la question ; viewer = refus ; erreurs sans détail de schéma. **MOYEN-1 clos** : « Calculé » ne lit que `store.trusted` (tables `audit_*` créées par le code au démarrage, ex. `audit_ref_budget` synthétique via `SOVEREIGN_AUDIT_REFERENCE_DIR`) ou un jeu certifié à jour ; toute table de `formula_inputs` (modèle par défaut + secteurs) est non remplaçable pour tous les rôles (409, échec fermé) ; tout dépôt passe par `DataStore.assert_user_loadable` (y compris la synchro planifiée) ; le run enregistre `table_fingerprint` du contenu réel. `formula_scope` (entité, exercice) : absent = le chat demande. Ouvert : P-085 (dépôt viewer). Doc : `docs/formules-financieres.md` ; évaluation : `python -m eval.run_formula_routing`.
- **Contrôles d'audit (P-075)** : `app/audit_rules/` + `rules/audit/AUD001..010.yaml` (SQL du dépôt, valeurs de paramètres validées puis formatées en littéraux ; `docs/controles-audit.md`). Modifier une règle = nouvelle `version`. Tables réservées `audit_rule_runs`/`audit_findings`. Vocabulaire « signal de risque à examiner », jamais « fraude ». AUD007 inactif (pas de champ bancaire). **D-5 : s'arrêter ici, valider l'utilité avec un premier utilisateur avant P-076/P-077.** `rules/audit/` doit rester non inscriptible en production.
- **Benchmark mondial (2026-11-15)** : `docs/benchmark-2026-11.md` (Power BI et 4 autres familles, aspect par aspect, 16 idées priorisées) ; propositions P-065 à P-068 (mesures + synonymes, SDMX + métadonnées, abonnements courriel, sécurité par ligne) en attente d'accord
- **Projets voisins (même session, 2026-11-15)** : Code de la Route DJ (`c6806da`, poussé) et Loiyale ex-Vigile (`/home/kali/loi25`, dépôt privé `robkira01-max/loiyale`, https://loiyale.vercel.app) ont reçu pages légales, SEO/partage, vraie 404 et en-têtes de sécurité ; DeepfakeDetector et PlagiatDetect supprimés (archives du code dans `~/Downloads/archives_projets/`)
- **Clés à setter** : `COMTRADE_API_KEY` (UN Comtrade Plus, ligne commentée dans `.env`)

## Stack

| Couche | Technologie |
|--------|-------------|
| Backend | FastAPI + DuckDB — `app/` |
| Frontend | React 18 + Vite + TypeScript — `frontend/` |
| Cartes | MapLibre GL + PMTiles + GeoJSON |
| LLM | KimiClient (Groq) + fallback Ollama — `LLM_PROVIDER=kimi|ollama` |
| Tests clés viewer | `X-Api-Key: test-viewer-key-s6` |
| Tests clés editor | `X-Api-Key: test-editor-key-s6` |

## Composants carte et visualisation disponibles

| Composant | Tile type | Usage |
|-----------|-----------|-------|
| `MapLibreMap` | `map` | Choroplèthe ADM1 (6 régions DJ) |
| `MapAdm2` | `map-adm2` | Choroplèthe ADM2 / quartiers DJ-ville, toggle niveau |
| `BivariateChoropleth` | `map-bivariate` | 2 variables, matrice 3×3 |
| `TradeFlowMap` | `trade-flow-map` | Flux commerciaux Port DJ animés |
| `HeatmapTile` | `heatmap` | Calendrier de chaleur SVG 1D/2D, 4 palettes |
| `GeoCatalog` | — | Catalogue couches géospatiales, viewer + editor |

## Catalogue géospatial (P-022)

- `data/geo/catalog.yaml` — registre maître (source de vérité licences + statut)
- `app/geo_catalog/models.py` — `GeoLayer`, `GeoCatalog`, `LayerWarning`
- `app/geo_catalog/registry.py` — `load_catalog()`, `get_layer()`, `toggle_layer()`
- `GET /api/v1/geo/catalog` — liste (filtre `?enabled_only=true`)
- `GET /api/v1/geo/catalog/{id}` — métadonnées d'une couche
- `PUT /api/v1/geo/catalog/{id}/toggle` — activer/désactiver (editor)
- Règle : toute nouvelle couche géographique doit être enregistrée dans `catalog.yaml` avec licence vérifiée avant usage.

## Import géographique (P-024)

- `app/geo_catalog/importer.py` — `import_layer()` : validation DuckDB Spatial, extraction métadonnées, sanitisation nom, enregistrement `catalog.yaml` en `status: draft`
- `POST /api/v1/geo/import` — multipart, editor only, 50 Mo max, liste d'extensions, guard path traversal
- `GeoImport.tsx` — formulaire drag-and-drop, champs métadonnées, callback `onImported`
- Formats supportés : `.geojson`, `.json`, `.gpkg`, `.parquet`
- Isolation tests : fixture `monkeypatch` sur `_CATALOG_PATH` + `_IMPORTS_DIR` pour ne pas polluer `catalog.yaml`

## Analyses spatiales avancées (P-025)

- Analyses ajoutées à `spatial_engine.py` : `buffer` (lon/lat/radius_km → features + dist_m triés), `intersection` (deux couches → paires feature_a/feature_b/overlap_km2), `density` (area_km2 par polygone, ou density_per_km2 si value_col)
- `AnalyzeRequest.layer_id_b` (str|None) dans `geo_spatial.py` — validé alphanumérique comme `layer_id`
- `SpatialAnalysis.tsx` — UI d'analyse spatiale : sélecteur type + couche A, params contextuels (buffer: lon/lat/rayon ; intersection: couche B ; density: colonne valeur), tableau résultats dynamique

## Moteur spatial (P-023)

- `app/geo_catalog/spatial_engine.py` — `SpatialEngine` (DuckDB Spatial 1.5.6)
- Analyses : `area` (km² spheroid), `centroid` (lon/lat), `bbox`, `nearest` (lon/lat, limit), `summary`
- `GET /api/v1/geo/analyze/types` — liste des analyses disponibles
- `POST /api/v1/geo/analyze` — `{layer_id, analysis, params}` → `{results}`
- Sécurité : `layer_id` alphanumérique uniquement ; `file_path` lu du catalog uniquement (jamais de l'utilisateur) ; path guard = résolution sous `_PROJECT_ROOT`.

## Données géographiques

- `data/geo/dji_adm1.geojson` — 6 régions ADM1 (GADM, CC BY 4.0)
- `data/geo/dj_adm2.geojson` — 6 districts enrichis (pop/densité/superficie)
- `data/geo/dj_quartiers.geojson` — 11 quartiers Djibouti-ville (**approximatifs**, OSM ODbL)
- `tools/download_dj_geo.py` — téléchargement GADM v4.1 + OSM Overpass (run une fois)
- `GET /api/v1/geo/dj/{adm1|adm2|quartiers}` — route FastAPI

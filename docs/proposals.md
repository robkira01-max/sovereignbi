# Proposals hors-plan — MizanBI

Ajoutées le 2026-11-06. Chaque proposition inclut la raison et l'impact estimé.

---

## P-022 — Catalogue géospatial centralisé MizanGeo ✅

**Raison :** Les couches ADM1, ADM2 et quartiers existaient sans registre commun. Un catalogue centralisé permet de référencer chaque couche avec sa source, sa licence, ses avertissements qualité, et son statut de validation — base nécessaire avant tout moteur d'analyse spatiale.
**Impact :** Élevé — gouvernance des données géographiques, prérequis P-023 à P-029.
**Statut :** Livré 2026-11-08. `data/geo/catalog.yaml` (registre maître YAML, 3 couches DJ), `app/geo_catalog/` (models + registry avec cache + toggle), `GET /api/v1/geo/catalog` (liste + filtre enabled_only), `GET /api/v1/geo/catalog/{id}`, `PUT /api/v1/geo/catalog/{id}/toggle` (editor). `GeoCatalog.tsx` (cards statut/warning/toggle, viewer/editor). HeatmapTile livré en bonus. 24 pytest + 13 Vitest + 3 Vitest heatmap. 1178/1178 tests.

## P-022b — HeatmapTile (bonus, livré avec P-022)

**Raison :** Visualisation calendrier de chaleur 1D/2D pour données temporelles INSTAD (exportations par mois, flux par heure × région). Composant SVG pur, sans dépendance.
**Impact :** Faible/Moyen — nouveau type de tile utile pour séries temporelles.
**Statut :** Livré 2026-11-08. `HeatmapTile.tsx` (SVG, 4 palettes, 5 niveaux, mode 1D/2D), tile type `heatmap`, i18n `heatmap.*` (fr/en/ar/es). 3 pytest + 8 Vitest.

## P-023 — Moteur d'analyse spatiale DuckDB Spatial ✅

**Raison :** Après le catalogue, l'étape suivante est d'exécuter des requêtes spatiales sur les couches géographiques — aires, centroides, bounding boxes, proximité.
**Impact :** Élevé — analyse spatiale native sans PostGIS (DuckDB 1.5.6, `ST_Area_Spheroid`, `ST_Centroid`, `ST_Distance`).
**Statut :** Livré 2026-11-08. `app/geo_catalog/spatial_engine.py` (SpatialEngine, 5 analyses : area/centroid/bbox/nearest/summary, path guard projet root), `GET /api/v1/geo/analyze/types`, `POST /api/v1/geo/analyze`. `file_path` + `name_column` ajoutés à catalog.yaml + GeoLayer model. 23 pytest. 1201/1203 tests.

## P-024 — Import GeoJSON / GeoPackage / GeoParquet ✅ (2026-11-08)

**Raison :** Permettre à INSTAD d'importer ses propres données géographiques dans le catalogue.
**Impact :** Élevé pour l'autonomie utilisateur.
**Livré :** `importer.py` + `POST /api/v1/geo/import` + `GeoImport.tsx` + i18n 4 locales. 24 pytest + 10 Vitest. Formats : `.geojson/.json/.gpkg/.parquet`, 50 Mo max, enregistrement catalog.yaml en draft.

## P-025 — Analyses spatiales : buffers, proximité, intersections, densité ✅ (2026-11-08)

**Raison :** Cas d'usage concret INSTAD : « Quels districts sont à moins de 50 km d'un port ? »
**Impact :** Élevé — différenciateur BI+SIG.
**Livré :** `spatial_engine.py` +3 analyses (buffer/intersection/density), `layer_id_b` dans router. `SpatialAnalysis.tsx` (sélecteur analyse + couche, params contextuels : lon/lat/rayon, couche B, colonne valeur). i18n 4 locales. 16 nouveaux pytest (39 total spatial) + 11 Vitest. 1241/1243 pytest + 135/135 Vitest.

## P-026 — Interaction carte ↔ dashboards BI ✅ (2026-11-08)

**Raison :** Sélectionner une région sur la carte filtre automatiquement les KPIs et graphiques du dashboard.
**Impact :** Très élevé — expérience BI géospatiale unifiée.
**Livré :** `render_tile()` wrapping subquery avec WHERE clause + fallback gracieux si colonne absente. `?region=`/`?region_col=` validés (regex). `onRegionSelect`/`selectedRegion` props dans TileRenderer→MapLibreMap/MapAdm2. Badge région + bouton clear. `loadTileData` recharge sur changement région. MAP_TYPES exclus du filtre. i18n `map_filter.*` fr/en/ar/es. 11 pytest + 8 Vitest. 1252/1254 pytest · 143/143 Vitest.

## P-027 — Assistant GeoAI en langage naturel

**Raison :** « Affiche les régions où la densité est la plus élevée et compare avec le chômage » — interprété par le LLM, carte + KPIs générés.
**Impact :** Très élevé — différenciateur marché.
**Statut :** ✅ Livré 2026-11-08 (commit 7677a8e). `app/geo_catalog/geo_ai.py` + `app/routers/geo_ai.py` + `GeoAI.tsx`. 22 pytest + 8 Vitest. 1274/1276 pytest + 152/152 Vitest.

---

## Proposals mizanbi-client (frontend standalone React)

Le propriétaire a livré une version standalone React (`mizanbi-client/`) apportant les fonctionnalités P-028 à P-034.
App connectée au backend SovereignBI via `VITE_API_BASE`. Pas de MapLibre — cartes SVG inline. Stack : React 18, recharts, @tanstack/react-query, pdfjs-dist. Vitest ajouté pour P-034.

## P-028 — Thèmes OKLCH dynamiques ✅ (livré dans mizanbi-client)

**Raison :** 7 thèmes OKLCH (violet-green, teal-ochre, ocean, forest, sunset, plum-rose, light) + mode Auto (Djibouti→teal-ochre, Canada→violet-green) pour s'adapter à l'identité visuelle de chaque institution.
**Impact :** Élevé — identité de marque, démo institutionnelle.
**Statut :** ✅ Livré 2026-11-08. `src/lib/theme.ts` : `applyTheme()`, `colorForValue()`, `scaleFor()`, `textOnFill()`, `resolveTheme()`. Menu thème topbar (pastilles). `THEME_MODE_KEY` localStorage.

## P-029 — Cartes anciennes géoréférencées ✅ (livré dans mizanbi-client)

**Raison :** Visualiser les cartes historiques superposées aux contours administratifs modernes (utilisation pdfjs pour images raster + transformation affine).
**Impact :** Moyen — usage archivistique et pédagogique.
**Statut :** ✅ Livré 2026-11-08. `src/pages/AncientMaps.tsx` + `src/lib/ancientMaps.ts`. Upload PDF + contrôle de transparence + GCPs affines.

## P-030 — Bulletins d'information économique BIE 2001–2012 ✅ (livré dans mizanbi-client)

**Raison :** Données réelles du Ministère des Finances de Djibouti (snapshot local 8 nov. 2026). Évolution du PIB, inflation, recettes/dépenses, dette extérieure sur 12 ans.
**Impact :** Très élevé — données économiques nationales vérifiées, différenciateur pour INSTAD.
**Statut :** ✅ Livré 2026-11-08. `src/lib/bie.ts` + `src/data/bie/` (bie_series.json, bie_sources.json). Page `BiePage` avec graphiques ComposedChart (réel + prévisions ministère + modèle MizanBI), tableau récapitulatif annuel.

## P-031 — Tableau de bord national Canada (StatCan) ✅ (livré dans mizanbi-client)

**Raison :** Données StatCan (Licence ouverte, snapshot 2026-11-07) : chômage, emploi, IPC, population par province. Marché cible Canada.
**Impact :** Élevé — cohérence marché Canada.
**Statut :** ✅ Livré 2026-11-08. `src/lib/statcan.ts` + `src/data/statcan/` (5 JSON). Page `CanadaNationalPage` : chômage par province, variation emploi oct. 2026, IPC.

## P-032 — Utilisateur de démonstration Robleh Hassan ✅ (livré dans mizanbi-client)

**Raison :** Mode démo affiche "Robleh Hassan" (initiales RH) au lieu d'un placeholder générique. `DEMO_USER` exporté depuis `data/demo.ts`.
**Impact :** Faible — cosmétique/identité pilote.
**Statut :** ✅ Livré 2026-11-08. `DEMO_USER = { name: 'Robleh Hassan', initials: 'RH' }`. Token 'demo' → setUserName(DEMO_USER.name). localStorage `mizan_user_name`.

## P-033 — BCD 2024 + INSTAD RGPH-3 ✅ (livré dans mizanbi-client)

**Raison :** Données réelles : BCD Rapport Annuel 2024 (Synthèse p. 2-3) — 16 KPIs bancaires incluant crédits +35,4%, monnaie électronique ×4,3. INSTAD RGPH-3 (résultats définitifs juin 2025) — 1 066 568 habitants.
**Impact :** Très élevé — données bancaires et démographiques nationales vérifiées.
**Statut :** ✅ Livré 2026-11-08. `src/lib/bcd.ts` + `src/data/bcd/bcd_2024.json` + `src/data/instad/rgph3.json`. Page `BcdPage` : KPI cards, graphiques recharts.

## P-039 — Écran « changer mon mot de passe » + CI GitHub Actions ✅ (livré 2026-11-09)

## P-040 — Attribution de source sur les tuiles ✅ (livré 2026-11-11)
**Raison :** Les tableaux de bord institutionnels (INSTAD, BCD) doivent citer leurs sources sur chaque tuile, dans le Bulletin HTML, le PPTX et le CSV. Standard rapports officiels.
**Impact :** Moyen — `Tile.source`, `PUT /source`, affichage tuile, bulletin CSS `::before`, PPTX 8pt, CSV `# Source :`. 12 pytest. 1448/1448 tests.

## P-041 — Intégration données SIG CERD Djibouti-ville ✅ (livré 2026-11-11)
**Raison :** 10 couches vecteur UTM 38N fournies par le propriétaire (CERD) : écoles, équipements socio-éco, secteurs d'adressage, communes, îlots, bus, voirie, ouvrages, typologies urbaines. Conversion EPSG:32638 → WGS84 GeoJSON, enregistrement catalog.yaml en draft, 10 routes `/api/v1/geo/dj/cerd_*`.
**Impact :** Élevé — données urbaines Djibouti-ville pour analyse spatiale et visualisation. `tools/convert_cerd_shp.py`. 49 pytest. 1517/1517 tests.

## P-042 — Intégration données Santé INSTAD Djibouti 2020 ✅ (livré 2026-11-11)
**Raison :** Données XLSX Annuaire Statistiques Sanitaires 2020 (structures sanitaires, indicateurs de santé, PCIME enfants) fournies par le propriétaire. 73 structures, 65 avec GPS, 39 indicateurs, 66 structures PCIME.
**Impact :** Élevé — données santé réelles DJ. 3 tables DuckDB, GeoJSON `/structures_sante`, dashboard `sante-djibouti-2020.yaml`. 20 pytest. 1468/1468 tests.

## P-043 — Suppression arabe volet SIG (mizanbi-client) ✅ (livré 2026-11-11)
**Raison :** Pas de traduction arabe validée pour l'interface cartographique et spatiale. `SIG_LANGS = ['fr', 'en']`, auto-switch vers FR si langue AR quand on entre dans le volet SIG.
**Impact :** Faible — cosmétique + exactitude linguistique. 0 test impacté.

---

## P-050 — Fusion frontend/ + mizanbi-client/ : Phase 1 — base mizanbi-client

**Raison :** Deux frontends React coexistent, créant une dette de maintenance : features dans l'un absentes de l'autre, deux CI builds, deux bases i18n divergentes. Base retenue : `mizanbi-client/` (design dark OKLCH, population/BIE/BCD Canada, GeoAI, Admin, Auth).
**Impact :** Élevé / risqué — semaine de travail. Prérequis : tous les P-05x.
**Plan :** Mettre en place l'infrastructure commune (API client, types partagés, structure routes) dans `mizanbi-client/` avant de porter les composants.
**Statut :** ✅ Livré 2026-11-11 — `api.ts` types+méthodes, `i18n.ts` section dashboard (fr/en/ar), `LiveTileRenderer.tsx` (kpi/bar/line/pie/table/grid/grid-facettes). Fix curly-quote bug i18n (double-quote switch). 142→257 Vitest.

## P-051 — Fusion : Phase 2 — DashboardPage complète dans mizanbi-client

**Raison :** `frontend/` a toute la logique dashboard (tile CRUD, SQL editor pinné, export, source, annotations, tags, favoris, sharing, freshness). La migrer dans le design `mizanbi-client/`.
**Impact :** Élevé — c'est le cœur fonctionnel BI. Composants à porter : `DashboardPage.tsx`, `TableTile.tsx`, `SqlEditor.tsx`, `TileFreshnessBar.tsx`.
**Dépend de :** P-050
**Statut :** ✅ Livré 2026-11-11 — `Dashboards.tsx` réécrit (640 lignes) : liste+tags+favoris, vue détail, tile CRUD drag-and-drop, notes, source, freshness, AI insight, export bulletin/PPTX/CSV, clone, region filter badge. Mode démo préservé. 115 nouveaux tests → 257 Vitest.

## P-052 — Fusion : Phase 3 — Tiles avancées (map-bivariate, heatmap, trade-flow)

**Raison :** `BivariateChoropleth`, `HeatmapTile`, `TradeFlowMap`, `MapAdm2` existent dans `frontend/` mais pas dans `mizanbi-client/`. Composants autonomes, portage direct.
**Impact :** Moyen — spécialisation INSTAD et démos institutionnelles.
**Dépend de :** P-051
**Statut :** ✅ Livré 2026-11-11 — `BivariateChoropleth.tsx`, `HeatmapTile.tsx`, `TradeFlowMap.tsx`, `SparklineKpi.tsx`, `TableTile.tsx` portés dans `mizanbi-client/src/components/`. `maplibre-gl` + `pmtiles` ajoutés. ChatBI drawer flottant + palette pro 12 couleurs (P-052b+c). 257/257 Vitest.

## P-053 — Fusion : Phase 4 — Exports (Bulletin HTML, CSV par tuile)

**Raison :** Les boutons export de `frontend/` étaient absents de `mizanbi-client/`. Fonctionnalité principale pour les démos institutionnelles.
**Impact :** Élevé pour l'adoption — les rapports sont la valeur perçue principale.
**Dépend de :** P-051
**Statut :** ✅ Livré 2026-11-11 — `lib/exports.ts` (tileDataToCsv, dashboardToBulletinHtml, triggerDownload), `DemoDashboardDetail` pur JS (plus d'appel API), bouton CSV par tuile. 14 nouveaux tests. Commit `b0cb391`.

## P-054 — SIG complet : GeoImport, GeoCatalog, SpatialAnalysis dans mizanbi-client

**Raison :** `frontend/` avait ces composants UI (import drag-and-drop, moteur DuckDB Spatial). `mizanbi-client/` a déjà le volet SIG cartographique mais pas l'interface d'administration des couches.
**Impact :** Moyen — complète le volet SIG de mizanbi-client.
**Statut :** ✅ Livré 2026-11-13 — `GeoCatalog.tsx`, `GeoImport.tsx`, `SpatialAnalysis.tsx` créés avec guard `isApiConfigured()`, i18n fr+en complétées (57 clés), intégrés dans `Sig.tsx` + `App.tsx` (prop `isEditor`), 17 tests Vitest. Commit `8999f3c`.

## P-056 — Validation cartographique Djibouti-ville ✅ (livré 2026-11-13)

**Raison :** Données géographiques `dj_quartiers.geojson` et `cerd_communes.geojson` contenaient deux erreurs : (1) `density_km2` = copie de `population_est` au lieu de la vraie valeur calculée ; (2) labels CERD "4/5 eme arrondissement" sans préciser la commune ; (3) catalogue indiquait 2 communes au lieu de 3 (Boulaos, Ras-Dika, Balbala). Le propriétaire a demandé une image cartographique de référence à soumettre aux autorités djiboutiennes pour validation.
**Impact :** Moyen — exactitude des données, prérequis validation institutionnelle.
**Livré :** `dj_quartiers.geojson` (+density_km2 UTM 38N, +area_km2, +commune attribution provisoire, +validation_status) ; `cerd_communes.geojson` (relabels Balbala 4ème/5ème +commune_nom +arrondissement +note) ; `catalog.yaml` (description 3 communes, warning Boulaos/Ras-Dika absents). Image PNG cartographique `/tmp/djibouti_admin_map.png` livrée pour validation terrain. 1517/1517 tests. Commit `b39e24e`.

## P-057 — Découpage officiel CERD admin_pol (91 quartiers, 3 communes) ✅ (livré 2026-11-14)

**Raison :** Les shapefiles CERD ne couvraient que Balbala (arr. 4 et 5) ; le centre-ville (Boulaos, Ras-Dika) n'avait que 11 quartiers OSM approximatifs en rectangles. Le propriétaire a fourni `admin_pol.shp` (CERD, photogrammétrie 1/2 500, 2014).
**Impact :** Élevé — premier fond de carte complet et officiel de Djibouti-ville.
**Livré :** conversion ITRF2005 → WGS84 (`.shx` régénéré), `data/geo/admin_quartiers.geojson` (91) + `admin_communes.geojson` (3), routes `/api/v1/geo/dj/admin_quartiers|admin_communes`, entrées `catalog.yaml` (licence CERD, `draft`), fond partagé `VilleBaseLayers` pour les 4 cartes Djibouti-ville, `getQuartierForPoint` sur les vrais quartiers. Commits `da5bda7`, `aaaa3cb`, `5be5dae`.

## P-058 — Routes et bâtiments OSM de Djibouti-ville ✅ (livré 2026-11-14)

**Raison :** Complément en attendant les données CERD des arrondissements 1 à 3 (voirie du centre absente).
**Impact :** Moyen — voirie du centre (1 875 tronçons) + 98 239 bâtiments (ODbL, Geofabrik 2026-11-14).
**Livré :** `osm_centre_voirie` (embarquée), `osm_batiments.geojson.gz` (remplacé le 2026-11-15 par le levé CERD, voir P-063), catalogue + attribution ODbL. Commits `810b8c3`, `71d6bb0`, `5a37e64`. **Reste :** vérification visuelle de la couche bâtiments contre l'API réelle (après redéploiement Oracle).

## P-059 — Attribution automatique des sources de cartes ✅ (livré 2026-11-14)

**Raison :** Les pieds de carte « Source : … » étaient codés en dur dans chaque composant ; une correction de licence demandait d'éditer plusieurs fichiers.
**Impact :** Moyen — une seule source de vérité (`catalog.yaml`).
**Livré :** `tools/sync_geo_attribution.py` → `geo_attribution.json` → composant `GeoSources` (3 cartes Djibouti-ville) ; `tests/test_geo_attribution_sync.py` échoue si désynchronisé. **Reste :** généraliser `GeoSources` aux autres cartes (`DjiboutiMap`, `EcolesMap`, `Bulletins`…). Commit `5a37e64`.

## P-061 — Documents juridiques, cookies et acceptation des CGU ✅ (livré 2026-11-14)

**Raison :** Le propriétaire a fourni quatre documents juridiques (confidentialité, CGU, cookies, mentions légales). L'audit a relevé : texte « les données ne quittent jamais votre serveur » faux avec un fournisseur d'IA externe, « cookie de session » inexact (le jeton est en `sessionStorage`), pages légales et bannière visibles seulement après connexion, lien « politique » de la bannière qui refusait au lieu d'ouvrir la page, polices de cartes chargées depuis un serveur tiers, aucune acceptation des CGU enregistrée.
**Impact :** Élevé — prérequis de toute diffusion à de vrais utilisateurs.
**Livré :** pages Confidentialité / CGU / Cookies / Mentions légales fr+en (`legalContent.ts`, config unique `legalConfig.ts`, bandeau « version de travail », placeholders surlignés), accessibles avant connexion ; bannière corrigée + « Gérer mes cookies » ; `TermsGate` + `POST /compliance/consent/self` (allowlist de finalités `cgu|privacy:AAAA-MM`, identité de la session, pas d'IP) ; `/compliance/notice` reflète `LLM_PROVIDER` ; glyphes de cartes hébergés localement ; tests de garde (clés de stockage documentées, aucun tiers, garde-fou de publication). **Reste (propriétaire) :** compléter `legalConfig.ts`, validation par un juriste, durées de conservation, procédure d'incident, choix du fournisseur d'IA et du droit applicable, puis `draft: false`. **À relire par un humain :** la route `/compliance/consent/self` (contrôle d'accès).

## P-062 — Durcissement web MizanBI et outil d'audit de lancement ✅ (livré 2026-11-14)

**Raison :** Cahier des charges « points techniques 3 à 20 » du propriétaire. Audit : clé API injectable dans le navigateur, mesure d'audience appelée sans consentement, image OG en SVG (non rendue par LinkedIn/Facebook), sitemap invalide, favicons incomplets, « soft 404 », un seul titre pour toute l'application, 3,8 Mo de JavaScript au premier chargement.
**Impact :** Élevé — sécurité (point 3), conformité cookies (point 5), partage et SEO (6-9, 15), performance (12).
**Livré :** voir CLAUDE.md « Durcissement web » ; `tools/web_launch_audit.py` (15 tests, réutilisable sur tous les projets web) ; `tools/make_brand_assets.py`. Premier audit des sites déjà en ligne : Vigile (aucune balise OG, robots, sitemap ni page légale) et Code de la Route DJ (lien cassé `/fr/verify`, image de 493 Ko, pas de robots/sitemap/OG/pages légales). **Reste (propriétaire) :** décider site vitrine séparé vs application (URLs `/features`, `/pricing`, `/docs`, `/contact` impossibles dans l'application actuelle sans URL par page) ; renseigner `VITE_SITE_URL` en production ; Lighthouse sur l'URL publique ; HSTS et redirection HTTPS côté serveur de production (non vérifiables depuis le dépôt).

## P-065 — Mesures réutilisables et synonymes dans la couche sémantique ✅ (livré 2026-11-15)

**Raison :** Inspiré de DAX (Power BI) et des couches sémantiques (Wren AI, dbt) : définir une fois chaque mesure (taux de chômage, chiffre d'affaires…) avec ses synonymes, pour que « chômage », « sans-emploi » et « taux de chômage » renvoient au même calcul. Gain mesuré de +17 à +23 points de précision avec une couche sémantique (PLAN.md §1.2).
**Impact :** Élevé — précision de l'IA ; Moyen en développement (extension de `semantic/model.yaml`, tests d'éval).
**Livré :** `app/semantic/resolver.py` (reconnaissance déterministe des termes avant l'appel au LLM : insensible à la casse, aux accents et au pluriel, plus longue expression d'abord, synonymes de 3 caractères ou moins sensibles à la casse pour que « ça » ne devienne pas « CA »), `app/semantic/validate.py` (doublons, alias ambigus, SQL illisible, colonnes/tables inconnues), modèle étendu (filtres nommés, synonymes de valeurs, alias de colonnes, unités), routes `GET /semantic/validate` et `GET /semantic/resolve` (viewer), `semantic/model.yaml` enrichi (3 filtres, 4 régions avec synonymes, unités). Les définitions reconnues sont placées en tête du prompt. 32 tests.
**Défauts corrigés en chemin :** (1) `get_graph` ne transmettait au LLM que le glossaire et les règles : les mesures, tables et jointures du modèle v2 n'étaient jamais dans le prompt ; (2) un secteur activé passait un objet `SemanticModel` qui s'affichait comme sa représentation Python (`SemanticModel(...)`) au lieu de son texte. **Non mesuré :** l'effet sur la précision (aucun modèle de génération installé sur cette machine ; la ligne de base de `eval/BASELINE.md` n'a jamais été établie). À mesurer sur une machine avec modèle local avant d'annoncer un gain. Le prompt est plus long qu'avant (modèle complet) : à surveiller avec un petit modèle.

## P-066 — Métadonnées d'indicateurs et import/export SDMX-CSV ✅ (livré 2026-11-15)

**Raison :** Les instituts de statistique (cible INSTAD) échangent via SDMX (.Stat Suite, MIT). Associer à chaque indicateur sa source, périodicité, définition et unité ; importer/exporter en SDMX-CSV/ML.
**Impact :** Élevé pour le marché institutionnel ; Moyen/Élevé en développement.
**Livré :** (1) métadonnées d'indicateur sur les mesures du modèle sémantique (`code`, `source`, `frequency` en codes SDMX A/S/Q/M/W/D/H/B/N, `definition`, `methodology`, `topic`, `last_updated`, `unit`) validées par `validate_model` (code unique, périodicité, date) ; `GET /semantic/indicators[/{code}]` (catalogue du modèle actif, avec la liste de ce qui manque) ; modèle INSTAD : 4 indicateurs documentés. (2) `app/sdmx/csv_format.py` : écriture et lecture **SDMX-CSV 2.0** (lecture de la 1.0 aussi), identifiants de composants normalisés, périodes SDMX (2024, 2024-Q1, 2024-03, 2024-03-15), neutralisation des formules (`=`, `+`, `@`), erreurs avec numéro de ligne. (3) `GET /dashboards/{id}/tiles/{id}/export/sdmx-csv` (colonnes temps et valeur déduites ou précisées, `structure_id`, `unit`, `freq`). (4) `POST /sdmx/import` (éditeur) : validation, `dry_run`, table `sdmx_*` à préfixe forcé (aucune table existante ne peut être écrasée), `replace`, limite de taille, refus du XML et de l'action D. 66 tests.
**Limites assumées :** SDMX-CSV seulement (**pas de SDMX-ML**, pas d'API REST SDMX, pas de DSD ni de codelists réelles) ; une observation par ligne ; fichier produit non validé avec l'outil officiel d'un registre SDMX (à faire avant diffusion) ; agence par défaut `MIZANBI`, à remplacer par l'agence réelle de l'institut ; pas d'interface (bouton d'export) dans le client. Défaut corrigé en chemin : DuckDB renvoie les décimaux en `Decimal`, ce qui empêchait de reconnaître la colonne de valeurs. **Reste :** SDMX-ML, bouton dans le client, page publique de diffusion (idée 13 du benchmark).
**Bouton d'export dans le client (livré 2026-11-15) :** « ↓ SDMX » à côté de « ↓ CSV » sur chaque tuile d'un tableau de bord (`components/SdmxExportButton.tsx`, `lib/sdmx.ts`). Petit formulaire : identifiant du jeu (AGENCE:ID(VERSION)), unité, périodicité (A, S, Q, M, W, D) ; champs vides = valeurs déduites par le serveur. Validation côté client alignée sur le serveur (bouton désactivé tant qu'un champ est invalide), erreurs du serveur affichées telles quelles, noms de fichier et identifiants assainis (aucune injection dans l'URL). La note du formulaire rappelle l'agence par défaut MIZANBI et que le fichier n'est pas validé avec un registre officiel. 20 tests Vitest. **Vérifié dans un navigateur réel** (backend isolé) : formulaire, refus d'un identifiant invalide, téléchargement d'un fichier SDMX-CSV correct. **Non vérifié en navigateur :** l'affichage d'une erreur du serveur (tuile sans colonne numérique). Bouton d'import livré ensuite (voir ci-dessous).
**Import dans le client (livré 2026-11-15) :** carte « Import SDMX-CSV » sur la page Import (éditeur ou admin) : `components/SdmxImport.tsx`, `lib/sdmxImport.ts`. **Deux temps** : « Vérifier le fichier » (`dry_run`, rien n'est chargé : résumé du jeu, nombre d'observations, colonnes, table cible `sdmx_…`) puis « Charger dans la base », **actif seulement pour la requête exactement vérifiée** (changer le fichier, le nom de table ou la case « Remplacer » oblige à revérifier). Refus côté client du XML (SDMX-ML), des fichiers vides ou de plus de 50 Mo, des noms de table invalides ; messages du serveur affichés tels quels (numéro de ligne) ; table existante → invite à cocher « Remplacer ». La note rappelle : pas de SDMX-ML, pas de validation contre une structure (DSD) officielle, une table non importée en SDMX n'est jamais écrasée. 11 tests Vitest (418 au total). **Vérifié dans un navigateur réel** (backend isolé) : fichier valide (vérification sans chargement, puis chargement), changement de nom exigeant une revérification, doublon (409), fichier invalide (« Ligne 3 : OBS_VALUE non numérique »), fichier XML refusé. **Non testé :** import d'un fichier volumineux (limite 50 Mo), SDMX-CSV 1.0 depuis le navigateur (couvert côté serveur seulement).
**Pas d'import dans le client pour :** SDMX-ML, ni l'action D (suppression), ni plusieurs fichiers à la fois.

## P-067 — Abonnements courriel aux bulletins ✅ (livré 2026-11-15)

**Raison :** Inspiré des abonnements Power BI et de Tableau Pulse : bulletin envoyé à date fixe, « les chiffres du jour » sans poser de question. S'appuie sur le Bulletin HTML (P-002) et le moteur d'alertes existants.
**Impact :** Moyen — valeur d'usage immédiate ; Faible/Moyen en développement (envoi de courriels à configurer).
**Livré :** abonnement d'une adresse à un tableau de bord (quotidien, hebdomadaire ou mensuel, heure UTC, jour) ; `POST/GET/DELETE /subscriptions` et `POST /subscriptions/{id}/send-now` (éditeur : les adresses sont des données personnelles) ; `GET /subscriptions/status` ; envoi planifié par le planificateur existant (tâche chaque minute, l'échéance réelle est calculée par `is_due`, une seule tentative par échéance, l'échec d'un abonné n'arrête pas les autres, l'erreur reste visible). Bulletin = `generate_bulletin_html` existant, titre échappé. SMTP avec STARTTLS obligatoire ; **sans `SMTP_HOST`, rien n'est envoyé** : les messages vont dans `data/outbox/*.eml`. Désabonnement par jeton HMAC par abonné (GET = formulaire seulement, POST = suppression, car les antivirus de messagerie préchargent les liens) ; seule route sans `RequireRole`, exception voulue. Garde-fous : rejet des retours à la ligne (injection d'en-têtes), liste blanche de domaines optionnelle, 50 abonnés max par tableau, fichier en 0600, erreurs SMTP sans détails ni identifiants. 28 tests.
**Limites assumées :** jamais testé contre un vrai serveur SMTP (seulement l'échec et la boîte d'envoi) ; pas de consentement du destinataire (double opt-in) : l'éditeur qui ajoute une adresse en est responsable, à encadrer dans le DPA (P-064) et la Loi 25/PIPEDA ; pas de « résumé IA » dans le courriel (le bulletin n'inclut un commentaire IA que s'il est fourni) ; pas d'interface dans le client ; stockage JSON (pas de base) ; une instance du serveur seulement (deux instances enverraient en double) ; ni pièces jointes PDF ni rejeu après panne prolongée (l'échéance manquée est envoyée une fois au retour). **Reste :** double opt-in, interface, résumés IA, file d'envoi avec reprise.
**Écran dans le client (livré 2026-11-15) :** bouton « ✉ Abonnements » dans la barre d'outils d'un tableau de bord (éditeur ou admin seulement), panneau `components/SubscriptionsPanel.tsx` + `lib/subscriptions.ts` : liste des abonnés (calendrier en clair, dernier envoi, dernière erreur), ajout (adresse, fréquence, heure UTC, jour), « Envoyer maintenant » et « Supprimer » avec confirmation en deux temps. **Le panneau dit clairement quand SMTP n'est pas configuré** (« aucun courriel réel n'est envoyé ») ; l'ajout exige une case « le destinataire a accepté de recevoir ce bulletin » (pas de double opt-in côté serveur) ; la note rappelle la Loi 25/PIPEDA et que la sécurité par ligne refuse les bulletins. 14 tests Vitest. **Vérifié dans un navigateur réel** (backend isolé) : ouverture du panneau, ajout, envoi vers la boîte d'envoi locale (message correct, fichier 0600), suppression. **Non revérifié en navigateur** après coup : le libellé « Chaque semaine / Chaque mois » du menu de fréquence (corrigé, couvert par un test de rendu). **Non testé :** envoi réel par SMTP, et l'affichage d'une erreur du serveur (doublon 409, bulletin refusé).
**Défaut existant corrigé en passant (hors plan, 1 ligne) :** la sous-navigation (`App.tsx`) était `sticky` avec `top: 56` alors que `<main>` est déjà le conteneur de défilement sous l'en-tête : elle restait collée 56 px trop bas et **recouvrait la barre d'outils des tableaux de bord** (Bulletin, Dupliquer, PPTX, Tuile et le nouveau bouton étaient inaccessibles à la souris). `top: 0` corrige : vérifié en navigateur (boutons cliquables).

## P-068 — Sécurité par ligne ✅ livrée 2026-11-15 (jeux de données certifiés : P-069 proposée)

**Raison :** Un utilisateur ne voit que sa région ou son périmètre (à vérifier d'abord : l'existence d'une sécurité par ligne dans le code n'est pas confirmée) ; pastille « validé par l'INSTAD » sur chaque source, liée au certificat de précision.
**Impact :** Élevé pour banques et administrations ; Moyen/Élevé en développement.
**Statut :** accord reçu 2026-11-15, **en attente de 3 décisions de conception** (voir ci-dessous). Constat du code : **aucune sécurité par ligne n'existe**. (a) `RequireRole` ne renvoie que le rôle ; l'identité de l'utilisateur n'atteint pas les routes. (b) Les clés API (viewer/editor/admin) n'ont pas d'identité, donc pas de périmètre. (c) ~10 endroits exécutent du SQL (`/ask`, tuiles, exports, bulletins, alertes, MCP, abonnements) : un filtre oublié sur un seul = fuite. (d) Les bulletins courriel (P-067) s'exécutent sans utilisateur : ils enverraient toutes les lignes. Piste sûre : réécriture sqlglot (chaque table protégée devient `(SELECT * FROM t WHERE col IN (...))`) appliquée à **un seul point d'étranglement**, échec fermé.

**Livré (décisions du propriétaire : comptes web seulement ; échec fermé ; bulletins refusés sur tables protégées) :** `app/security/row_policy.py` (règles `data/row_policies.yaml` : table, colonne, périmètre), réécriture sqlglot de **chaque** référence à une table protégée en sous-requête filtrée dans `DataStore.execute` (seul passage vers DuckDB) et dans les exemples envoyés au LLM ; `PrincipalMiddleware` (identité → ContextVar) ; périmètres par compte en base d'authentification ; `GET /security/row-policies` (diagnostic), `GET/PUT /security/users/{id}/scopes[/{scope}]` (admin, audités sans les valeurs). Admin (compte ou clé) voit tout ; compte non-admin voit son périmètre ; **sans périmètre, clé API viewer/editor, jeton d'intégration/partage, planificateur, courriel : refus.** Caches partagés coupés tant que des règles existent (`/ask`, `/export/pdf-cached`, insights) ; cache persistant purgé au démarrage ; remplacement d'une table protégée par un non-admin refusé ; fonctions de table refusées. Fichier de règles invalide, clé mal écrite, vide ou chemin explicite introuvable = **actif et refus** (jamais « sans protection »). `AccessDenied` → 403. 45 tests.
**Relecture `security-reviewer` (2026-11-15) :** aucun contournement de la réécriture trouvé (CTE, récursif, LATERAL, FROM-first, `TABLE`, `SUMMARIZE`, erreurs de cast, injection par valeur de périmètre, propagation du contexte dans LangGraph/threadpool). 7 constats corrigés : fichier mal formé = protection coupée en silence (HIGH), `/export/pdf-cached` (MEDIUM), comptes de lignes du MCP (MEDIUM), remplacement de table (LOW), fonctions de table (LOW), clé de cache (LOW), garde défensive. **Relecture du propriétaire encore due** (règle du dépôt).
**Limites :** la sécurité s'applique aux **valeurs exactes** d'une colonne (comparaison texte, sensible à la casse) ; une colonne de périmètre doit exister dans chaque table protégée ; les clés API viewer/editor ne voient aucune table protégée (par décision) ; les noms de colonnes et de tables restent visibles ; l'admin voit tout, y compris dans les exemples du prompt IA ; les agrégats d'une table non protégée dérivée de données protégées ne sont pas couverts ; DuckDB est en processus unique avec le serveur (pas d'isolation OS) ; le conteneur Excel/add-in n'a pas été testé avec des règles ; règles lues sur le disque du serveur (pas d'éditeur dans l'interface).

## P-065 — Mesures réutilisables et synonymes dans la couche sémantique ✅ (livré 2026-11-15)

**Raison :** Inspiré de DAX (Power BI) et des couches sémantiques (Wren AI, dbt) : définir une fois chaque mesure (taux de chômage, chiffre d'affaires…) avec ses synonymes, pour que « chômage », « sans-emploi » et « taux de chômage » renvoient au même calcul. Gain mesuré de +17 à +23 points de précision avec une couche sémantique (PLAN.md §1.2).
**Impact :** Élevé — précision de l'IA ; Moyen en développement (extension de `semantic/model.yaml`, tests d'éval).
**Livré :** `app/semantic/resolver.py` (reconnaissance déterministe des termes avant l'appel au LLM : insensible à la casse, aux accents et au pluriel, plus longue expression d'abord, synonymes de 3 caractères ou moins sensibles à la casse pour que « ça » ne devienne pas « CA »), `app/semantic/validate.py` (doublons, alias ambigus, SQL illisible, colonnes/tables inconnues), modèle étendu (filtres nommés, synonymes de valeurs, alias de colonnes, unités), routes `GET /semantic/validate` et `GET /semantic/resolve` (viewer), `semantic/model.yaml` enrichi (3 filtres, 4 régions avec synonymes, unités). Les définitions reconnues sont placées en tête du prompt. 32 tests.
**Défauts corrigés en chemin :** (1) `get_graph` ne transmettait au LLM que le glossaire et les règles : les mesures, tables et jointures du modèle v2 n'étaient jamais dans le prompt ; (2) un secteur activé passait un objet `SemanticModel` qui s'affichait comme sa représentation Python (`SemanticModel(...)`) au lieu de son texte. **Non mesuré :** l'effet sur la précision (aucun modèle de génération installé sur cette machine ; la ligne de base de `eval/BASELINE.md` n'a jamais été établie). À mesurer sur une machine avec modèle local avant d'annoncer un gain. Le prompt est plus long qu'avant (modèle complet) : à surveiller avec un petit modèle.

## P-066 — Métadonnées d'indicateurs et import/export SDMX-CSV ✅ (livré 2026-11-15)

**Raison :** Les instituts de statistique (cible INSTAD) échangent via SDMX (.Stat Suite, MIT). Associer à chaque indicateur sa source, périodicité, définition et unité ; importer/exporter en SDMX-CSV/ML.
**Impact :** Élevé pour le marché institutionnel ; Moyen/Élevé en développement.
**Livré :** (1) métadonnées d'indicateur sur les mesures du modèle sémantique (`code`, `source`, `frequency` en codes SDMX A/S/Q/M/W/D/H/B/N, `definition`, `methodology`, `topic`, `last_updated`, `unit`) validées par `validate_model` (code unique, périodicité, date) ; `GET /semantic/indicators[/{code}]` (catalogue du modèle actif, avec la liste de ce qui manque) ; modèle INSTAD : 4 indicateurs documentés. (2) `app/sdmx/csv_format.py` : écriture et lecture **SDMX-CSV 2.0** (lecture de la 1.0 aussi), identifiants de composants normalisés, périodes SDMX (2024, 2024-Q1, 2024-03, 2024-03-15), neutralisation des formules (`=`, `+`, `@`), erreurs avec numéro de ligne. (3) `GET /dashboards/{id}/tiles/{id}/export/sdmx-csv` (colonnes temps et valeur déduites ou précisées, `structure_id`, `unit`, `freq`). (4) `POST /sdmx/import` (éditeur) : validation, `dry_run`, table `sdmx_*` à préfixe forcé (aucune table existante ne peut être écrasée), `replace`, limite de taille, refus du XML et de l'action D. 66 tests.
**Limites assumées :** SDMX-CSV seulement (**pas de SDMX-ML**, pas d'API REST SDMX, pas de DSD ni de codelists réelles) ; une observation par ligne ; fichier produit non validé avec l'outil officiel d'un registre SDMX (à faire avant diffusion) ; agence par défaut `MIZANBI`, à remplacer par l'agence réelle de l'institut ; pas d'interface (bouton d'export) dans le client. Défaut corrigé en chemin : DuckDB renvoie les décimaux en `Decimal`, ce qui empêchait de reconnaître la colonne de valeurs. **Reste :** SDMX-ML, bouton dans le client, page publique de diffusion (idée 13 du benchmark).

## P-067 — Abonnements courriel aux bulletins ✅ (livré 2026-11-15)

**Raison :** Inspiré des abonnements Power BI et de Tableau Pulse : bulletin envoyé à date fixe, « les chiffres du jour » sans poser de question. S'appuie sur le Bulletin HTML (P-002) et le moteur d'alertes existants.
**Impact :** Moyen — valeur d'usage immédiate ; Faible/Moyen en développement (envoi de courriels à configurer).
**Livré :** abonnement d'une adresse à un tableau de bord (quotidien, hebdomadaire ou mensuel, heure UTC, jour) ; `POST/GET/DELETE /subscriptions` et `POST /subscriptions/{id}/send-now` (éditeur : les adresses sont des données personnelles) ; `GET /subscriptions/status` ; envoi planifié par le planificateur existant (tâche chaque minute, l'échéance réelle est calculée par `is_due`, une seule tentative par échéance, l'échec d'un abonné n'arrête pas les autres, l'erreur reste visible). Bulletin = `generate_bulletin_html` existant, titre échappé. SMTP avec STARTTLS obligatoire ; **sans `SMTP_HOST`, rien n'est envoyé** : les messages vont dans `data/outbox/*.eml`. Désabonnement par jeton HMAC par abonné (GET = formulaire seulement, POST = suppression, car les antivirus de messagerie préchargent les liens) ; seule route sans `RequireRole`, exception voulue. Garde-fous : rejet des retours à la ligne (injection d'en-têtes), liste blanche de domaines optionnelle, 50 abonnés max par tableau, fichier en 0600, erreurs SMTP sans détails ni identifiants. 28 tests.
**Limites assumées :** jamais testé contre un vrai serveur SMTP (seulement l'échec et la boîte d'envoi) ; pas de consentement du destinataire (double opt-in) : l'éditeur qui ajoute une adresse en est responsable, à encadrer dans le DPA (P-064) et la Loi 25/PIPEDA ; pas de « résumé IA » dans le courriel (le bulletin n'inclut un commentaire IA que s'il est fourni) ; pas d'interface dans le client ; stockage JSON (pas de base) ; une instance du serveur seulement (deux instances enverraient en double) ; ni pièces jointes PDF ni rejeu après panne prolongée (l'échéance manquée est envoyée une fois au retour). **Reste :** double opt-in, interface, résumés IA, file d'envoi avec reprise.

## P-068 — Sécurité par ligne et jeux de données certifiés 📋 (proposée 2026-11-15)

**Raison :** Un utilisateur ne voit que sa région ou son périmètre (à vérifier d'abord : l'existence d'une sécurité par ligne dans le code n'est pas confirmée) ; pastille « validé par l'INSTAD » sur chaque source, liée au certificat de précision.
**Impact :** Élevé pour banques et administrations ; Moyen/Élevé en développement.
**Statut :** proposée, **ne pas implémenter sans accord**.

## P-064 — Contrat de traitement des données (DPA), incidents, export/suppression 📋 (proposée 2026-11-15)

**Raison :** Pour vendre à des banques, ONG et administrations, les CGU ne suffisent pas : il faut un DPA (responsable/sous-traitant, instructions du client, mesures de sécurité, sous-traitants techniques, transferts internationaux, suppression/restitution, gestion des incidents). Audit du dépôt : mesures de sécurité réelles et documentées, mais aucun outil de purge/export de compte (le registre de demandes accepte « delete »/« export » sans procédure), aucune procédure ni registre d'incident, sauvegardes seulement en objectifs (RTO < 1 h, RPO < 24 h). La politique de confidentialité nomme l'entreprise responsable du traitement même pour les données importées par le client (à scinder : responsable pour comptes/journaux, sous-traitant pour les données importées).
**Impact :** Élevé pour la vente B2B ; Moyen en développement (outil d'export/suppression + registre d'incidents).
**Proposé :** DPA type fr/en avec annexes alignées sur le code (annexes sous-traitants/transferts après décision hébergement et fournisseur d'IA) ; séparation des rôles dans `legalContent.ts` ; procédure d'incident ; outil d'export et de suppression des données d'un compte. À valider par un juriste. **Ne pas implémenter sans accord du propriétaire.**

## P-063 — Levé topographique CERD 1/2 500 (bâtiments, routes, hydro, rail, sites) ✅ (livré 2026-11-15)

**Raison :** Le propriétaire a fourni l'archive complète du levé photogrammétrique CERD (même projet que `admin_pol`, 2014) : 112 417 bâtiments typés, routes, hydrographie, voie ferrée, réseaux. Plus précis et mieux classé que les données OSM.
**Impact :** Élevé — fond officiel complet de Djibouti-ville, bâtiments par usage (écoles, mosquées, santé, administrations, commerces…).
**Livré :** `tools/convert_cerd_topo.py`, 5 couches `cerd_*.geojson.gz` + catalogue (licence CERD, `draft`, avertissement « levé de 2014 »), routes API, `lib/topoLayers.ts` + `TopoCanvas`, légende des catégories, attribution automatique ; l'OSM des bâtiments est supprimé (l'OSM des routes du centre reste). 16 tests pytest + 6 Vitest. **Reste :** intégrer si besoin `centre_lin` (axes, noms RN1/RN2…), `contour` (courbes de niveau), `road_lin`, `utilit_*`, `vegetation` ; valider la licence par écrit.

## P-060 — Carte ADM2/quartiers (`MapAdm2`) sur les quartiers officiels ✅ (livré 2026-11-14)

**Raison :** Le niveau « quartiers » utilisait les 11 quartiers OSM approximatifs (avertissement « données approximatives »).
**Impact :** Moyen — 91 quartiers officiels, jointure tolérante aux accents/casse/apostrophes (`lib/adm2Levels.ts`), popup échappé (commune, superficie).
**Livré :** `MapAdm2` sur `admin_quartiers` (propriété `nom`), 7 tests Vitest. **Attention :** les jeux de données existants clés sur les anciens noms (« Balbala Nord », « Centre-ville »…) ne se joindront plus ; les tuiles `map-adm2` au niveau quartiers doivent utiliser les noms officiels. `dj_quartiers` reste dans le catalogue (non utilisé par le client).

## P-055 — Suppression frontend/ et finalisation CI

**Raison :** `frontend/` devenu redondant une fois `mizanbi-client/` complet. Éliminer la dette de maintenance.
**Impact :** Faible (cleanup) — irréversible mais snapshot git conservé.
**Statut :** ✅ Livré 2026-11-11 — `frontend/` supprimé (74 fichiers), service `mizanbi-client` activé dans `docker-compose.server.yml`, Q-002 et Q-003 fermées. Commit `5cb2627`.

**Raison :** `POST /auth/password` existait (P-037) sans interface utilisateur ; les 48+ commits n'avaient aucun workflow CI.
**Impact :** Moyen — autonomie utilisateur (tout rôle peut changer son propre mot de passe) + CI sur push/PR.
**Statut :** ✅ Livré 2026-11-09. `ChangePasswordModal.tsx` (champs current/new/confirm, toggle show/hide, messages d'erreur localisés, état succès). `accounts.ts` : `changePassword()` dans l'interface + API (POST /auth/password, mappage 403→wrongPassword) + démo (validation seule). `i18n.ts` : section `changePwd` fr/en/ar. `App.tsx` : bouton cadenas près du déconnexion (masqué en mode démo). `.github/workflows/ci.yml` : lint ruff + py_compile → pytest unitaires → tsc + Vitest + npm build. Ruff 0 violations dans app/. 127/127 Vitest, 1436/1436 pytest.

## P-038 — Écran administrateur des comptes ✅ (livré 2026-11-08)

**Raison :** P-037 exposait la gestion des comptes uniquement par API/CLI ; l'INSTAD a besoin d'un écran.
**Impact :** Élevé — autonomie des administrateurs du pilote.
**Statut :** ✅ Livré 2026-11-08. `mizanbi-client` : page `Admin.tsx` (liste, création, rôle en ligne, désactivation en deux temps, réinitialisation de mot de passe), `lib/accounts.ts` (service API + simulation démo aux mêmes règles), `ApiError` (statut + détail), i18n fr/en/ar, entrée de navigation visible aux seuls admins (rôle lu via `/auth/me`). **Bug serveur trouvé en testant dans un vrai navigateur :** CORS n'autorisait pas `PATCH`, donc le changement de rôle aurait échoué en production (corrigé + tests de pré-contrôle). 39 tests Vitest. Vérifié en navigateur : démo, connecté (vrai backend), arabe/RTL, compte lecteur (entrée masquée, API 403). **À faire relire par un arabophone.**

## P-037 — Gestion des comptes par rôle ✅ (livré 2026-11-08)

**Raison :** Après la revue (rôle par utilisateur), il n'existait aucun moyen de créer un compte autre qu'`admin` (seul `seed_admin`).
**Impact :** Élevé — prérequis multi-utilisateurs du pilote INSTAD.
**Statut :** ✅ Livré 2026-11-08. `app/auth/users_router.py` (`GET/POST /auth/users`, `PATCH /auth/users/{id}`, `PUT /auth/users/{id}/password`, `POST /auth/password`), garde dernier admin atomique, révocation de sessions, audit chaîné, `tools/create_user.py`. Relu security-reviewer (0 critique/élevé ; 2 moyens + 8 faibles corrigés). 100+ tests dédiés. **Reste hors périmètre :** interface d'administration des comptes (proposition ouverte).

## P-036 — i18n GeoAI (fr/en/ar) ✅ (livré 2026-11-08)

**Raison :** Les textes de la page GeoAI et ses réponses de démonstration étaient codés en français.
**Impact :** Moyen — cohérence trilingue de l'app standalone (Arabe/RTL pour l'INSTAD).
**Statut :** ✅ Livré 2026-11-08. Section `geoai` dans `i18n.ts` (fr/en/ar), démos localisées (nombres par langue, chiffres latins en arabe), détection des questions en 3 langues, garde anti-injection fr/ar, langue transmise au backend. Prose « pauvreté » corrigée (une affirmation non vérifiée retirée). **Bug préexistant corrigé en vérifiant dans le navigateur :** `buildDjiboutiMap` plantait l'app entière (Polygon traité comme MultiPolygon). **À faire relire par un arabophone** avant diffusion (traductions ar rédigées sans relecture humaine).

## P-034 — Bulletins enrichis multi-sources ✅ (livré 2026-11-08)

**Raison :** La page Bulletins n'utilisait que les données démo. Intégration des données réelles BIE (macro DJ), BCD 2024 (système bancaire DJ) et StatCan (emploi Canada) en 3 onglets analytiques avec export HTML multi-sections.
**Impact :** Élevé — bulletin de synthèse prêt à distribuer aux institutionnels.
**Statut :** ✅ Livré 2026-11-08. `src/lib/bulletins.ts` (fonctions pures : `bieBulletinSection`, `bcdBulletinSection`, `statcanBulletinSection`, `renderBulletinHtml`). `Bulletins.tsx` refactorisé : 4 onglets (Hebdomadaire/Économie DJ/Banques DJ/Canada), export HTML auto-suffisant multi-sections. Vitest setup (`vitest.config.ts`, `package.json test`). 21/21 tests.

## P-035 — Page GeoAI dans mizanbi-client ✅ (livré 2026-11-08)

**Raison :** Bridger le backend GeoAI (P-027 `POST /api/v1/geo/ai-query`) avec l'interface standalone mizanbi-client. Mode démo précalculé depuis REGIONS (3 questions : chômage / population+densité / pauvreté > 30 %).
**Impact :** Élevé — IA géospatiale accessible dans l'app standalone, sans MapLibre.
**Statut :** ✅ Livré 2026-11-08. `src/lib/geoai.ts` (types, `guardInjection` 10 patterns, `parseGeoAIResult`, 3 démos depuis REGIONS). `src/pages/GeoAI.tsx` (questions rapides, textarea 500 chars, mode démo/connecté, prose card, MapHint + lien SIG, table résultats, raisonnement collapsible). Route `geoai` dans `App.tsx`. 16 tests Vitest. 37/37 tests total mizanbi-client.

---

## P-001 — Small multiples (tile type `grid`) ✅
**Raison :** Pour les 6 régions de Djibouti, afficher 6 mini-graphiques côte à côte est plus lisible qu'un seul barplot. Standard ONS UK, INSEE, KNBS.  
**Impact :** Moyen — pur frontend, 2-3 jours. Idéal pour les dashboards INSTAD.  
**Statut :** Livré 2026-11-06 (commit 5617e1a). `options.facet_by` + `options.chart_type` (bar|line).

## P-002 — Bulletin narratif HTML ✅
**Raison :** Le benchmark montre que les INS (ONS UK, Statistics Canada) remplacent leurs PDF par des bulletins web narratifs. MizanBI génère un HTML auto-suffisant depuis les YAML de dashboard.  
**Impact :** Élevé — artefact distribuable sans accès à la plateforme, ouvrable offline.  
**Statut :** Livré 2026-11-06 (commit 8061c6d). `GET /dashboards/{id}/export/bulletin` + bouton "↓ Bulletin" i18n.

## P-003 — Offline tiles Protomaps PMTiles ✅
**Raison :** Pour la démo terrain Djibouti (connectivité limitée), ajouter une carte de base offline (rues, bâtiments) en plus du choroplèthe ADM1 déjà livré.  
**Impact :** Moyen — bbox DJ : `41.7,10.9,43.6,12.8`, environ 10-30 Mo. 1-2 jours d'intégration.  
**Statut :** Livré 2026-11-06. `MapLibreMap.tsx` (MapLibre GL BSD-3 + pmtiles Apache-2), basemap PMTiles + couche choroplèthe auto-update, `GET /tiles/{file}.pmtiles`, `tools/download_pmtiles.py`. 982/984 pytest + 44/44 Vitest.

## P-004 — Choroplèthe bivariée ✅
**Raison :** 2 variables sur la même carte (pauvreté × chômage, 3×3 classes) est un standard des INS modernes.  
**Impact :** Faible/Moyen — surtout utile pour les rapports, pas pour la démo pilote.  
**Statut :** Livré 2026-11-06. `BivariateChoropleth.tsx` (MapLibre GL), type `map-bivariate`, palettes `classic` / `teal-orange`, terciles égaux, légende 3×3, hover popup dual. 982/984 pytest + 46/46 Vitest (+2 tests).

## P-005 — Flux commerciaux Kepler.gl ✅
**Raison :** Visualiser les flux port de Djibouti → Éthiopie serait un atout fort pour les démos institutionnelles (UNCTAD, Banque mondiale).  
**Impact :** Faible en pilote, élevé en phase expansion. Kepler.gl MIT, s'intègre en iframe.  
**Statut :** Livré 2026-11-07. `TradeFlowMap.tsx` (MapLibre + SVG arcs animés, CARTO dark basemap), 5 corridors DJ→ET (Addis/Dire Dawa/Mekele/Dessie/Hawassa), `GET /api/v1/trade-flows`, tile bento HomePage span 4. 10 tests pytest + 8 Vitest. 1025/1027 pytest + 54/54 Vitest (2 pre-existing).

## P-006 — Connecteurs KNBS Kenya / NISR Rwanda ✅
**Raison :** APIs ouvertes disponibles gratuitement, données téléchargeables directement. Stratégique pour l'expansion Afrique de l'Est.  
**Impact :** Moyen — 2-3 jours par connecteur. À faire après le pilote Djibouti.  
**Statut :** Livré 2026-11-06. `KNBSClient` + `NISRClient` (CKAN, SSRF guard, circuit breaker, licence check), 4 routes (`/connectors/knbs/search`, `/connectors/knbs`, `/connectors/nisr/search`, `/connectors/nisr`), CLIs `tools/ingest_knbs.py` + `tools/ingest_nisr.py`. 33 tests. 1015/1017 pytest (2 pre-existing).

## P-007 — Template narratif ONS (scrollytelling) ✅
**Raison :** `ONSvisual/svelte-scrolly` est open source (MIT), utilisé par l'ONS UK pour les bulletins web. Adapter en React pour les rapports INSTAD.  
**Impact :** Élevé pour les publications officielles INSTAD, neutre pour le pilote.  
**Statut :** Livré 2026-11-07. `ScrollySection` (IntersectionObserver, sticky figure + scrolling steps), `ScrollyPage` rapport Djibouti chômage 5 étapes (trend/choropleth/barh/youth/forecast), lien "Lire l'analyse →" dans HomePage. `employment_dj.ts` module partagé. 12 Vitest. 66/66 tests.

## P-008 — MCP server MizanBI ✅
**Raison :** Exposer les dashboards comme outils pour agents LLM (pattern Rill Data). Permettrait à Claude Code ou tout agent MCP de lire et créer des dashboards programmatiquement.  
**Impact :** Élevé à terme pour l'écosystème, neutre pour le pilote.  
**Statut :** Livré 2026-11-07. `GET /mcp/info` (public), `POST /mcp/rpc` (JSON-RPC 2.0, auth requise), 5 outils (`mizan_list_dashboards`, `mizan_get_dashboard`, `mizan_get_tile_data`, `mizan_list_tables`, `mizan_create_dashboard`), stdio wrapper `tools/mcp_server.py` pour Claude Code. 17 tests. 1042/1044.

## P-009 — Sparkline + Delta badge pour tuiles KPI ✅
**Raison :** Standard Power BI/ThoughtSpot : afficher la variation vs période précédente (↑ +12,3%) et une mini-sparkline sur les KPIs. Crucial pour les indicateurs INSTAD (chômage, PIB, inflation). Zéro LLM — calcul SQL pur DuckDB.  
**Impact :** Élevé pour les dashboards institutionnels, immédiat.  
**Statut :** Livré 2026-11-07. `app/dashboards/delta.py` (détection colonne date, agrégation MoM/YoY/WoW, 12/5/10 points), `GET /dashboards/{id}/tiles/{id}/delta`, `SparklineKpi.tsx` (SVG pur + badge ↑↓→), opt-in via `options.sparkline=true` dans TileRenderer. 12 pytest + 8 Vitest. 1054/1056 pytest, 74/74 Vitest.

## P-010 — Export PowerPoint (PPTX) ✅
**Raison :** Les institutions (INSTAD, IGAD, OIM) font leurs rapports en PowerPoint. `python-pptx` (MIT) permet de générer des slides depuis les YAML de dashboard — titre sur fond coloré, KPI centré géant, tableau ou liste, disclaimer de conformité sur chaque slide.  
**Impact :** Élevé pour les institutions, complémentaire au bulletin HTML (P-002).  
**Statut :** Livré 2026-11-07. `app/dashboards/pptx_export.py`, `GET /dashboards/{id}/export/pptx`, bouton "↓ PPTX" i18n (fr/en/ar/es). 11 pytest. 1065/1067.

## P-011 — Traffic light KPI (seuils colorés) ✅
**Raison :** Visualisation standard pour les indicateurs à seuils réglementaires (chômage ≤ 10% vert, ≤ 20% orange, > 20% rouge). Sans IA, purement déterministe : liste ordonnée de règles, première correspondance gagne, entrée sans op/value = fallback par défaut.  
**Impact :** Faible/Moyen — ajout de valeur immédiat pour les dashboards INSTAD et les rapports de conformité.  
**Statut :** Livré 2026-11-07. `app/dashboards/threshold.py` (`evaluate_threshold`, 6 opérateurs, DEFAULT_COLOR gris), `GET /dashboards/{id}/tiles/{id}/status`, `TileOptions.thresholds` + `evalThreshold()` dans `TileRenderer.tsx` (couleur appliquée sur `data-testid="tile-kpi-value"`). 12 pytest + 4 Vitest.

## P-012 — Export CSV par tuile ✅
**Raison :** Standard universel BI : permettre aux statisticiens INSTAD de télécharger les données brutes d'une tuile (Excel-compatible via BOM UTF-8). Complémentaire aux exports Bulletin/PPTX (P-002/P-010) : les institutions ont souvent besoin des données tabulaires, pas seulement des visuels.  
**Impact :** Faible/Moyen — ajout de valeur immédiat, zéro dépendance nouvelle.  
**Statut :** Livré 2026-11-07. `GET /dashboards/{id}/tiles/{id}/export/csv` (BOM UTF-8, `Content-Disposition: attachment`), bouton "↓ CSV" par tuile (`data-testid="export-csv-{id}"`) dans `DashboardPage`, i18n `export_csv` (fr/en/ar/es). 6 pytest + 1 Vitest.

## P-013 — Clonage de dashboard ✅
**Raison :** Standard BI universel — créer un dashboard District A, le cloner pour District B en changeant uniquement le scope ou les filtres SQL. Évite de recréer manuellement tous les tiles.  
**Impact :** Faible — 1 route + 1 bouton, zéro dépendance nouvelle.  
**Statut :** Livré 2026-11-07. `POST /dashboards/{id}/clone` (body optionnel `{new_id, title}`, conflict 409, invalid id 422, editor-only), bouton "⎘ Cloner" dans DashboardPage, i18n fr/en/ar/es. 7 pytest.

## P-014 — Favoris de dashboard ✅
**Raison :** Standard BI — marquer les dashboards les plus utilisés. Stockage léger JSON keyed par SHA-256 de l'API key (pas de DB nécessaire), isolation par utilisateur.  
**Impact :** Faible — UX immédiat, zéro dépendance.  
**Statut :** Livré 2026-11-07. `app/dashboards/favorites.py` (`toggle_favorite`, `get_favorites`, SHA-256 key hash), `POST /dashboards/{id}/favorite` (toggle), champ `is_favorite` dans `GET /dashboards`, bouton ★ per-item en liste, i18n fr/en/ar/es. 5 pytest.

## P-015 — Fraîcheur des données (freshness badge) ✅
**Raison :** Les tableaux de bord institutionnels (INSTAD) ont besoin de savoir si les données sont à jour. Badge coloré vert/orange/rouge dans chaque tuile, sans cache serveur — enregistrement de l'horodatage à chaque appel `/data`.  
**Impact :** Faible — UX immédiat, zéro dépendance externe.  
**Statut :** Livré 2026-11-07. `app/dashboards/tile_cache.py` (`record_execution`, `age_seconds`), `GET /dashboards/{id}/tiles/{id}/freshness`, badge `data-testid="freshness-dot-{id}"` dans DashboardPage, i18n fr/en/ar/es. 6 pytest.

## P-016 — Partage public de dashboard (lien en lecture seule) ✅
**Raison :** Permettre à INSTAD de partager un dashboard avec une agence externe (IGAD, Banque mondiale) sans compte. Token HMAC-SHA256 avec TTL, révocable. Routes publiques `/shared/{token}` sans authentification.  
**Impact :** Moyen — fonctionnalité de collaboration externe, zéro dépendance.  
**Statut :** Livré 2026-11-07. `app/dashboards/share.py` (`generate_share_token`, `validate_share_token`, `revoke_share_token`), `POST /dashboards/{id}/share` (editor, TTL configurable), `GET /dashboards/shared/{token}` + `/tiles/{id}/data` (public). 9 pytest.

## P-017 — Annotations textuelles sur les tuiles ✅
**Raison :** Les statisticiens INSTAD ont besoin d'annoter chaque tuile avec sa source (Recensement 2023, EDIM, etc.), sa méthodologie ou des mises en garde. Standard BI : Power BI et Tableau supportent les notes/descriptions par visuel.  
**Impact :** Faible/Moyen — ajoute de la valeur immédiate pour les rapports institutionnels, zéro dépendance.  
**Statut :** Livré 2026-11-07. `Tile.note` (str|None, 1 000 chars max), `PUT /dashboards/{id}/tiles/{id}/note` (editor-only), affichage italique gris sous le contenu, bouton ✎ inline pour éditer, `setTileNote()` dans `api/client.ts`, i18n fr/en/ar/es. 8 pytest + 2 Vitest.

## P-018 — Tri et filtrage des tables en navigateur ✅
**Raison :** Les tableaux de bord INSTAD affichent des tableaux de données brutes (par région, par secteur). Pouvoir trier par colonne (clic sur entête) et filtrer les lignes (recherche texte) sans requête serveur est un standard BI (Excel, Power BI, Tableau).  
**Impact :** Faible/Moyen — pur frontend, amélioration immédiate de l'utilisabilité, zéro dépendance.  
**Statut :** Livré 2026-11-07. Nouveau composant `TableTile.tsx` (sort asc/desc/none, filtre case-insensitive, état vide), `data-testid` sur chaque entête, `tile.table_filter_placeholder` i18n (fr/en/ar/es). 6 Vitest.

## P-019 — Étiquettes (tags) de dashboard ✅
**Raison :** À mesure que le nombre de dashboards croît (emploi, population, commerce, pilote, régions…), une catégorisation simple par étiquette permet de filtrer la liste sans chercher par titre. Standard BI (Tableau Server, Metabase).  
**Impact :** Faible — 1 route + 1 champ modèle + 1 input, zéro migration (YAML).  
**Statut :** Livré 2026-11-07. `Dashboard.tags: list[str]`, `PUT /dashboards/{id}/tags` (editor, max 20 × 50 chars), `GET /dashboards?tag=` filtre, chips cliquables + input édition dans `DashboardPage`, i18n fr/en/ar/es. 8 pytest.

## P-020 — Connecteur UN Comtrade Plus (flux commerciaux réels DJ) ✅
**Raison :** Les corridors P-005 sont fictifs. Comtrade Plus API (gratuit, 500 req/jour) fournit les vraies valeurs USD export/import de Djibouti (reporter 262) par partenaire. Fallback automatique sur données illustratives si la clé est absente.  
**Impact :** Moyen — données officielles ONU pour les démos institutionnelles (UNCTAD, Banque mondiale). Clé API gratuite.  
**Statut :** Livré 2026-11-07. `app/data/comtrade_client.py` (httpx, circuit breaker 3/60s, 10 partenaires géolocalisés), route `GET /api/v1/trade-flows?year=&flow=X|M` mise à jour (source=comtrade|demo), `tools/ingest_comtrade.py` (--dry-run, cache JSON), `COMTRADE_API_KEY` dans `.env.example`. 12 pytest.

## P-021 — Choroplèthe ADM2 + Quartiers Djibouti-Ville ✅
**Raison :** Au-delà des 6 régions ADM1 déjà disponibles, les décideurs INSTAD ont besoin de visualiser des indicateurs à l'échelle des districts enrichis (population, densité) et des quartiers de Djibouti-ville (11 quartiers — Balbala, Centre-ville, Arhiba, etc.). Données : GADM v4.1 (CC BY 4.0) + OSM Overpass (ODbL) ; délimitations quartiers approximatives à valider avec la mairie.  
**Impact :** Élevé pour les démos institutionnelles (planification urbaine, eau, santé). Zéro dépendance nouvelle.  
**Statut :** Livré 2026-11-07. `data/geo/dj_adm2.geojson` (6 districts + pop/densité), `data/geo/dj_quartiers.geojson` (11 quartiers), `GET /api/v1/geo/dj/{adm1|adm2|quartiers}`, `MapAdm2.tsx` (choroplèthe ADM2 + toggle niveau + tooltip population), tile type `map-adm2`, `tools/download_dj_geo.py` (GADM + Overpass), i18n `map.*` (fr/en/ar/es). 13 pytest + 6 Vitest.

---

## Livrées cette session

| Référence | Description | Commit |
|-----------|-------------|--------|
| **Choroplèthes ADM1** | ECharts + GeoJSON Djibouti, 4 palettes, 4 tiles INSTAD | f58fdf9 |
| **Tile data endpoint** | GET /dashboards/{id}/tiles/{id}/data — SQL exécuté côté serveur | 1fbf6e4 |
| **Insight IA** | GET /dashboards/{id}/tiles/{id}/insight — phrase LLM + badge IA | 1fbf6e4 |
| **P-001 Small multiples grid** | type: grid — mini-charts par facette, 2 tiles INSTAD | 5617e1a |
| **P-002 Bulletin HTML** | GET /export/bulletin — HTML auto-suffisant, tables, insights, disclaimer | 8061c6d |


## P-069 — Jeux de données certifiés ✅ livré 2026-11-15 (API + pastille client)

**Raison :** dernière partie de l'idée 4 du benchmark, séparée de P-068 : afficher une pastille sur une table ou un indicateur quand l'institut (ex. INSTAD) l'a validé, liée au certificat de précision existant (`app/accuracy/certificate.py`, HMAC).
**Impact :** Moyen (confiance, diffusion officielle) ; Faible en développement (registre signé + affichage).
**Livré :** registre `app/certification/registry.py` + `POST /certification` (admin : table, institution, référence de la validation, date de fin optionnelle), `POST /certification/{id}/revoke`, `GET /certification` et `GET /certification/{table}` (viewer : pastille `certified | stale | expired | revoked | tampered | none`, sans donnée de ligne), `GET /certification/{table}/history` (admin). **L'empreinte du contenu (lignes + schéma, indépendante de l'ordre) est calculée à la certification : dès que les données changent, la pastille passe à « stale »** (une certification ne couvre jamais des données qu'elle n'a pas vues). Signature HMAC (même secret que le certificat de précision) : toute modification du fichier de registre donne `tampered`. Historique conservé, audit sans le nom de l'institution, fichier en 0600, registre illisible jamais écrasé. 20 tests.
**Ce que la pastille ne prouve PAS :** un administrateur du serveur enregistre qu'une institution a validé ; **MizanBI ne vérifie pas l'institution** (message renvoyé à chaque appel). La confiance est celle accordée à l'administrateur. La signature n'est pas vérifiable par un tiers sans le secret du serveur. Ne pas la présenter comme une certification officielle de l'INSTAD tant que l'INSTAD n'a pas confirmé par écrit le processus.
**Écran d'administration (livré) :** section « Jeux de données certifiés » dans Paramètres › Comptes (admin) : liste des tables avec leur pastille, formulaire (table, institution, référence, date de fin facultative, case de confirmation obligatoire), bouton Révoquer avec motif. Bouton d'enregistrement désactivé tant que le formulaire est incomplet ; messages du serveur affichés tels quels ; mode démo : message, aucun formulaire. **Vérifié dans un navigateur réel** (backend temporaire + Playwright) : enregistrement, pastille verte sur l'accueil, passage à « Modifié depuis la validation » après changement des données, révocation. Défaut trouvé à cette occasion et corrigé : la couleur « validé » suivait le thème (ocre dans le thème Teal/Ocre, confondable avec un avertissement) ; teintes fixes désormais. 19 tests Vitest au total pour la certification.
**Pastille dans le client (livrée) :** `mizanbi-client/src/lib/certification.ts` (logique pure), `components/CertificationBadge.tsx`, textes fr/en, affichée à côté de chaque table chargée sur l'accueil. Icône + texte (jamais la couleur seule), infobulle avec institution, référence, date et la mention « MizanBI ne vérifie pas l'institution » ; un statut inconnu ou une réponse mal formée n'affiche **rien** (jamais un « validé » par défaut) ; échec de l'appel (non connecté, droits) = pas de pastille, pas d'erreur. 13 tests Vitest. Vérifiée dans un navigateur réel ; en mode démo, sans API, aucune pastille n'apparaît.
**Limites / reste :** pastille seulement sur l'accueil (pas dans le chat, les tuiles ni les bulletins) ; l'écran n'affiche pas l'historique des certifications (API `GET /certification/{table}/history`) ; pas d'écran pour les abonnements courriel ni l'export SDMX (boutons non demandés) ; l'empreinte relit toute la table (coût proportionnel à sa taille à chaque consultation de la liste) ; pas de lien avec les tuiles/bulletins ni les exports SDMX ; une table remplacée par des données identiques reste « certified » (c'est voulu) ; pas de signature asymétrique (clé publique) pour une vérification externe.


## P-070 — Mode strict de l'IA ✅ (livré 2026-11-15 ; actif par défaut avec un LLM externe, décision du propriétaire)

**Raison :** de nombreux clients (banques, administrations) refusent qu'un fournisseur d'IA externe (Kimi K3 notamment) reçoive leurs données. Constat du code : sans réglage, l'IA reçoit 3 lignes d'exemple par table, jusqu'à 50 lignes de résultat, des extraits de documents, les lignes de chaque tuile (insights demandés **automatiquement** à l'ouverture d'un tableau de bord), les réponses précédentes du chat et des messages d'erreur citant des valeurs.
**Livré :** `SOVEREIGN_AI_STRICT` — `app/ai_policy.py`. **Activation : `1` actif, `0` désactivé, vide/absent = automatique, c'est-à-dire actif dès que `LLM_PROVIDER` n'est pas `ollama`** (une valeur mal orthographiée compte comme externe), inactif avec le modèle local ; un avertissement est émis au démarrage si le mode est désactivé à la main avec un LLM externe. En mode strict : schéma seul dans le prompt SQL (plus d'exemples de lignes) ; réponse rédigée **localement** (aucun résultat envoyé, un appel de moins) ; extraits de documents retirés ; valeurs citées dans les erreurs de retry masquées ; insights IA refusés (403) et cache coupé ; historique du chat réduit aux questions de l'utilisateur ; avis de confidentialité et DPA mis à jour ; avertissement au démarrage si LLM externe sans mode strict. tests « témoin » prouvant que sans le mode les valeurs partent bien (une valeur secrète ne doit apparaître dans aucun prompt en mode strict). `docs/securite.md`, `.env.example`.
**Ce qui part encore :** la question, les noms de tables et de colonnes, le modèle sémantique (mesures, filtres, synonymes), les questions/SQL des exemples d'apprentissage. Ces éléments peuvent être sensibles : le mode strict **réduit** la fuite, il ne remplace pas un modèle local.
**Contreparties :** réponses moins rédigées (« 2 lignes (colonnes : …) » au lieu d'une phrase), moins de contexte sur les formats de valeurs, donc probablement une précision SQL moindre — **non mesurée** (aucun modèle de génération local pour lancer `eval.run_eval`). Pas de bouton dans l'interface (variable d'environnement seulement) ; le chat « général » reçoit toujours les noms de tables ; le géo-IA n'envoyait déjà aucune ligne (la prose est construite localement).
**Décision du propriétaire (2026-11-15) : actif par défaut avec un LLM externe.** Conséquences à connaître pour un déploiement qui utilise déjà `LLM_PROVIDER=kimi` (dont le pilote Djibouti) : à la prochaine mise à jour, les réponses deviennent « N lignes (colonnes : …) » au lieu d'une phrase, les insights IA des tuiles disparaissent (l'interface ignore l'erreur 403) et la précision du SQL peut baisser (**non mesurée**). Pour revenir au comportement précédent : `SOVEREIGN_AI_STRICT=0` (déconseillé, à documenter dans le DPA du client). 35 tests au total.
**Annexe D du DPA (livrée 2026-11-15) :** `docs/legal/dpa-fr.md` — fournisseur d'IA : identification, trois configurations (A local, B externe strict, C externe non strict), **tableau fonction par fonction des données transmises**, engagements à obtenir du fournisseur par écrit (entraînement, conservation, lieu, accès des autorités, incident, sous-traitants, suppression : **tous laissés à remplir, l'éditeur n'affirme rien à la place du fournisseur**), mesures techniques réelles, changements, limites, accord. Test `tests/test_dpa_consistency.py` : chaque variable et chaque route citée dans le DPA et la procédure d'incident doit exister dans le code. Il a trouvé **quatre erreurs de ma part** (une variable `KIMI_RPM` qui n'existe pas ici, `GET /audit/verify` qui n'existe pas ici, `PUT` au lieu de `PATCH` pour les comptes, `PUT` sans identifiant) : corrigées, et à l'origine de **P-071** (aucune vérification d'intégrité du journal d'audit n'existe).
**Indicateur dans l'interface (livré 2026-11-15) :** pastille dans l'en-tête (`components/AiModeBadge.tsx`, `lib/aiMode.ts`) lue depuis `GET /compliance/notice` (nouveaux champs `ai_provider` et `ai_external`) : « ● IA locale », « ◐ IA externe · strict » (vert), « ⚠ IA externe · non strict » (orange, seul état d'alerte). Infobulle : fournisseur, lieu des données et description complète du traitement. **Un état inconnu, une réponse mal formée ou une erreur n'affiche rien** (jamais un état rassurant par défaut). Icône + texte, teintes fixes. 11 tests Vitest (429 au total). **Vérifié dans un navigateur réel** pour les trois états (backend isolé, relancé avec chaque configuration) ; l'avertissement de démarrage a aussi été constaté. **Limite :** la pastille n'est visible que connecté et en mode API ; à largeur réduite, le bouton de thème passe sur plusieurs lignes à côté d'elle (cosmétique).
**Outil de mesure de la précision (livré 2026-11-15) :** `eval/compare_strict.py` (mesure appariée strict / ouvert, voir `eval/BASELINE.md`), 12 tests (statistiques connues, faux modèle qui n'a besoin des lignes d'exemple que pour réussir, reprise, restauration de l'environnement, question à référence cassée exclue). Les tests ont révélé deux défauts de l'outil, corrigés : colonnes de date lues comme du texte (7 requêtes de référence inexécutables) et référence cassée comptée contre le modèle. **Aucune mesure exploitable n'existe encore** : un seul essai de fonctionnement avec `llama3.2` (1 paire, inconclusif, 7 à 12 min par génération sur cette machine). **À faire sur une machine avec le modèle visé.**

## P-071 — Vérification d'intégrité du journal d'audit 📋 (proposée 2026-11-15)

**Raison :** le journal `data/audit.jsonl` est chaîné par SHA-256 (`app/feedback.py`) mais **aucune fonction ni route ne vérifie la chaîne** dans ce dépôt (`GET /audit/verify` appartient à LexBouti). Découvert en contrôlant le DPA et la procédure d'incident contre le code : ils citaient cette route, à tort (corrigé). Sans vérification, la chaîne ne prouve rien lors d'un incident.
**Proposé :** `verify_audit_chain()` + `GET /audit/verify` (admin) + test d'altération (ligne modifiée, supprimée, insérée, chaîne rompue), puis l'indiquer dans la procédure d'incident. **Impact :** Moyen (preuve en cas d'incident, argument DPA) ; Faible en développement. **Statut :** proposée, **ne pas implémenter sans accord**.

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

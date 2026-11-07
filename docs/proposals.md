# Proposals hors-plan — MizanBI

Ajoutées le 2026-11-06. Chaque proposition inclut la raison et l'impact estimé.

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

---

## Livrées cette session

| Référence | Description | Commit |
|-----------|-------------|--------|
| **Choroplèthes ADM1** | ECharts + GeoJSON Djibouti, 4 palettes, 4 tiles INSTAD | f58fdf9 |
| **Tile data endpoint** | GET /dashboards/{id}/tiles/{id}/data — SQL exécuté côté serveur | 1fbf6e4 |
| **Insight IA** | GET /dashboards/{id}/tiles/{id}/insight — phrase LLM + badge IA | 1fbf6e4 |
| **P-001 Small multiples grid** | type: grid — mini-charts par facette, 2 tiles INSTAD | 5617e1a |
| **P-002 Bulletin HTML** | GET /export/bulletin — HTML auto-suffisant, tables, insights, disclaimer | 8061c6d |

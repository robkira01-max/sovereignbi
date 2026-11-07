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

- **Tests** : `pytest` depuis la racine avec `.venv/bin/python` (Python 3.14 système n'a pas duckdb). 2 échecs pré-existants tolérés : `test_alert_crud_flow` + `test_embed_ask_with_valid_token_no_data`.
- **Vitest** : `cd frontend && npx vitest run`. `vi.mock()` factory : ne jamais référencer de variables module-level (hoisté avant initialisation) — inliner les données.
- **py_compile** : valider chaque fichier Python avant commit.
- **External URLs** dans `app/` : toute nouvelle URL base doit être ajoutée au lookahead regex de `tests/test_network_isolation.py`.
- **DeepSeek** : dev uniquement, données synthétiques, via `tools/dev_llm.py`. `app/` n'importe jamais `tools/`.
- **Licences** : MIT/Apache/BSD uniquement ; tenir `THIRD_PARTY.md` à jour.
- **Code** : anglais. **UI + docs** : français (anglais second).

## État courant (2026-11-07)

- **Tests** : 1151/1153 pytest + 93/93 Vitest
- **Dernière proposal** : P-021 ADM2 + Quartiers Djibouti-ville (`map-adm2`)
- **Commit** : `b3e3a76`
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

## Composants carte disponibles

| Composant | Tile type | Usage |
|-----------|-----------|-------|
| `MapLibreMap` | `map` | Choroplèthe ADM1 (6 régions DJ) |
| `MapAdm2` | `map-adm2` | Choroplèthe ADM2 / quartiers DJ-ville, toggle niveau |
| `BivariateChoropleth` | `map-bivariate` | 2 variables, matrice 3×3 |
| `TradeFlowMap` | `trade-flow-map` | Flux commerciaux Port DJ animés |

## Données géographiques

- `frontend/src/data/dji_adm1.geojson` — 6 régions ADM1 (GADM, CC BY 4.0)
- `data/geo/dj_adm2.geojson` — 6 districts enrichis (pop/densité/superficie)
- `data/geo/dj_quartiers.geojson` — 11 quartiers Djibouti-ville (**approximatifs**, OSM ODbL)
- `tools/download_dj_geo.py` — téléchargement GADM v4.1 + OSM Overpass (run une fois)
- `GET /api/v1/geo/dj/{adm1|adm2|quartiers}` — route FastAPI

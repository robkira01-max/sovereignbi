# P-027 — Connecteur Statistique Canada (WDS) — 7 novembre 2026

## Licence

Données sous la **Licence ouverte de Statistique Canada**
(https://www.statcan.gc.ca/en/terms-conditions/open-licence) :
licence mondiale, libre de redevances, non exclusive ; usage, reproduction,
publication, distribution et vente permis, y compris à des fins commerciales,
sans frais. Conditions :

- Attribution obligatoire à chaque usage :
  « Source : Statistique Canada, [nom du produit], [date de référence] ».
- Reproduction fidèle ; si les données sont modifiées, indiquer
  « Adapté de Statistique Canada ».
- Ne pas suggérer que Statistique Canada approuve MizanBI ou son usage ;
  ne pas utiliser son logo, son blason ni son nom de domaine comme marque.
- Ne pas tenter d'identifier une personne en fusionnant les données
  avec d'autres bases.
- Exclus de la licence : produits postaux et contenus dont un tiers
  détient la propriété intellectuelle.

Aucune clé API n'est requise : le Web Data Service (WDS) est public,
en accès libre.

## Tables vérifiées en direct (WDS, 7 novembre 2026)

| Table | Product ID | Titre (FR) | Période de référence | Publication |
|---|---|---|---|---|
| 14-10-0287-01 | 14100287 | Caractéristiques de la population active, données mensuelles désaisonnalisées et la tendance-cycle | oct. 2026 | 2026-11-06 |
| 17-10-0009-01 | 17100009 | Estimations de la population, trimestrielles | 1er juill. 2026 | 2026-09-23 |
| 18-10-0004-01 | 18100004 | Indice des prix à la consommation mensuel, non désaisonnalisé | sept. 2026 | 2026-10-19 |

Changement documenté : la table 14-10-0327-01 (14100327), d'abord envisagée
pour le chômage, est **annuelle par genre et groupe d'âge détaillé**, pas
mensuelle par province. Elle a été remplacée par la table mensuelle
14-10-0287-01 (14100287), vérifiée par `getCubeMetadata` (titre, fin
2026-10-01, publication 2026-11-06).

Séries retenues :
- Chômage : taux de chômage, Total - Genre, 15 ans et plus, estimation,
  désaisonnalisé, Canada + 10 provinces, oct. 2025 → oct. 2026.
- Population : estimations au 1er juillet, Canada + 10 provinces
  (territoires présents dans le CSV brut, non repris dans le snapshot),
  2022 → 2026.
- IPC : ensemble, Canada, 2002 = 100, non désaisonnalisé, sept. 2025 → sept. 2026.

## Valeurs clés du snapshot (spot-checks contre les CSV téléchargés)

- Chômage, Canada : **6,7 % en oct. 2026** (6,9 % en oct. 2025).
  Terre-Neuve-et-Labrador 8,7 % (10,2 % en oct. 2025),
  Québec 5,7 % (5,3 %), Ontario 7,3 % (7,6 %), Manitoba 5,0 % (5,9 %).
- Population, Canada : **41 798 407 au 1er juillet 2026**
  (41 608 982 au 1er juillet 2025). Ontario 16 262 121,
  Québec 9 067 114, Colombie-Britannique 5 710 598.
- IPC, Canada : **170,0 en sept. 2026** (164,9 en sept. 2025),
  soit **+3,1 % sur un an**.

## Méthode snapshot (hors ligne par design)

1. Appel WDS une seule fois, le 2026-11-07 :
   `GET https://www150.statcan.gc.ca/t1/wds/rest/getFullTableDownloadCSV/{product_id}/en`
   → lien ZIP → CSV complet (EPA : 1,18 Go décompressé, IPC : 161 Mo).
2. Extraction en streaming (script `/tmp/statcan/extract.py`, non livré
   dans le repo) : seules les lignes pertinentes sont gardées
   (dernières périodes, Canada + 10 provinces).
3. Snapshot local et léger : `src/data/statcan/` (16 Ko au total) —
   `statcan_chomage.json`, `statcan_population.json`, `statcan_ipc.json`,
   `statcan_sources.json` (product_id, nom exact, date de référence,
   date de téléchargement, URL WDS, licence).
4. Les CSV bruts volumineux ont été supprimés après extraction
   (ils ne sont pas dans le repo).
5. L'app lit **uniquement** le snapshot local en mode démo :
   aucune requête réseau StatCan au chargement.
   L'accès live optionnel (`fetchStatCanTable` dans `src/lib/statcan.ts`)
   exige `VITE_STATCAN_LIVE=1` et n'est jamais appelé par l'interface.

## Limites

- Snapshot figé au 7 novembre 2026 : à rafraîchir (voir README).
- Les chiffres canadiens sont **réels**, mais ils ne remplacent pas
  les chiffres de l'INSTAD Djibouti et ne doivent jamais être mélangés
  aux chiffres démo de Djibouti (1 030 000 hab. / 23,5 %) dans une même série.
- Le chômage StatCan (6,7 %, Canada, oct. 2026) et le chômage démo
  Djibouti (23,5 %) mesurent deux réalités différentes, avec deux
  méthodologies différentes : ne jamais les comparer directement
  sans l'expliquer.
- Aucune microdonnée confidentielle n'est utilisée.

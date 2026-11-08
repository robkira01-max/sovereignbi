# P-031 — Tableau de bord national Canada, d'après la maquette (8 novembre 2026)

## Ce qui vient de la maquette

Fichier fourni par Robleh : `~/workspace/user/files/56845_3_gcgm.webp`.
Mise en page reprise : onglets en haut (Vue d'ensemble, Population, Emploi, Régions,
Analyses, Exporter), navigation latérale (Tableau de bord, Population, Emploi &
Chômage, Cartographie, Rapports, Sources de données), 3 KPI en haut, graphique
« Croissance de l'emploi par province », carte « Répartition géographique » du
Canada avec légende Faible → Élevé, bandeau « Indicateurs clés — Répartition
par tranche d'âge », pied « © 2026 MizanBI • Données : Statistique Canada ».
Thème Violet/Vert (P-028), celui de la maquette. Nouvelle page
`src/pages/CanadaNational.tsx` (page `canadanat`), accessible depuis la
navigation et depuis la carte Canada de l'Accueil. La page Canada existante
(P-027) n'est pas modifiée.

## Ce qui a été vérifié — et ce qui a été corrigé

Vérification en direct via le WDS, table 14-10-0287-01, CSV complet téléchargé
le 8 novembre 2026, filtré sur Estimate, données désaisonnalisées, Total -
Gender, 15 ans et plus. Emploi en milliers de personnes, converti en emplois.
Snapshot : `src/data/statcan/statcan_emploi.json`.

| Chiffre de la maquette | Maquette | Vérifié (StatCan) | Statut |
|---|---|---|---|
| Chômage Canada, oct. 2026 | 6,7 % | 6,7 % | ✓ Vérifié (snapshot P-027) |
| Variation du chômage vs sept. 2026 | −0,3 pt | **+0,2 pt** (6,5 % → 6,7 %) | Corrigé |
| Population Canada | 41 798 407 | 41 798 407 | ✓ Vérifié (snapshot P-027) |
| Population vs 2025 | +0,8 % | **+0,5 %** (+189 425) | Corrigé |
| Emplois créés (mois) | 12 450 (+1 204) | **−4 700 emplois** (21 104 800 → 21 100 100) | Corrigé |
| Emploi par province | Ontario 3 120, Québec 2 540, C.-B. 1 890, Alberta 1 340, Manitoba 520, Saskatchewan 410, N.-É. 280 | Variations sept. → oct. 2026 : C.-B. +12 300, Québec +7 500, Saskatchewan +2 500, T.-N.-L. +2 900, N.-É. +2 300, N.-B. +1 200, Manitoba +800, Î.-P.-É. −1 300, Ontario −8 600, Alberta −24 300 | Corrigé |
| Tranches d'âge | 9,2 % / 68,5 % / 22,3 % | **12,6 % / 66,8 % / 20,5 %** (2 665 300 / 14 100 000 / 4 334 700 emplois ; chômage 13,7 % / 5,6 % / 5,5 %) | Corrigé |
| Région la plus active / croissance | Québec / Alberta +4,2 % | Plus forte hausse : C.-B. +12 300 ; plus forte baisse : Alberta −24 300 (chômage +0,9 pt, 6,4 % → 7,3 %) | Corrigé |

Aucun chiffre de la maquette non vérifiable n'est repris comme donnée réelle.
Les écarts sont listés dans la page elle-même (section Corrections).

## Ce qui n'a pas été repris de la maquette

- « Plan Pro, actif jusqu'au 31 déc. 2026 » et l'utilisatrice de la maquette :
  éléments de maquette, aucun utilisateur inventé, aucun abonnement ni paywall
  (modèle P-026 : licence annuelle par installation, sans quota).
- La carte du Canada est colorée par la **variation vérifiée de l'emploi**
  (et non par une « intensité d'activité économique » non définie) ; les
  territoires (Yukon, T.N.-O., Nunavut) sont en gris, sans série provinciale
  dans la table 14-10-0287-01.

## Carte

Contours simplifiés des 10 provinces + 3 territoires :
`src/data/ca_provinces.json` (62 Ko, Click That Hood, données ouvertes,
simplification Douglas-Peucker, tolérance ~0,15°, coordonnées arrondies à
0,01°). Projection équirectangulaire simple, dans la page. Les contours
simplifiés sont à valider avant toute démo institutionnelle ; pour des
contours officiels, utiliser les limites ouvertes de Statistique Canada.

## Fichiers

- `src/data/statcan/statcan_emploi.json` (nouveau), `src/data/statcan/statcan_sources.json`
  (entrée emploi ajoutée, téléchargement 2026-11-08), `src/lib/statcan.ts`
  (`STATCAN_EMPLOI`), `src/data/ca_provinces.json` (nouveau)
- `src/pages/CanadaNational.tsx` (nouveau), `src/App.tsx` (page `canadanat`),
  `src/pages/Home.tsx` (bouton), `src/lib/theme.ts` (`canadanat` → thème Canada
  en mode Auto), `src/lib/i18n.ts` (clés `canadaNational`, `canadaNationalSub`)

## Vérification

- `npm run build` : réussi, 523 modules, JS principal 901,83 Ko (gzip 254,04 Ko).
- Preview : index HTTP 200, JS HTTP 200.
- Aucune clé en dur. Aucune requête réseau en mode démo (snapshot local).

## P-032 — Nom d'utilisateur : Robleh Hassan (8 novembre 2026)

Aucun nom fictif du prototype ni de la maquette ne figurait dans le
code (noms des maquettes, jamais repris). La seule occurrence
fictive était l'utilisatrice de la maquette du tableau de bord Canada,
mentionnée uniquement dans les notes disant qu'elle n'était pas reproduite :
son nom a été retiré de `src/pages/CanadaNational.tsx` et de ce document.
L'app n'affichait aucun nom d'utilisateur (topbar : email seul), donc
« Robleh Hassan » a été ajouté comme utilisateur démo par défaut :
`DEMO_USER` dans `src/data/demo.ts` (initiales RH), ligne « Compte démo :
Robleh Hassan » sur le Login (`src/pages/Login.tsx`, clé i18n `demoAccount`
FR/EN/AR) et pastille RH + nom dans la topbar (`src/App.tsx`, persisté en
`localStorage` sous `mizan_user_name`). Aucun email, mot de passe ni rôle
inventé.

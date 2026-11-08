# P-033 — BCD 2024 + INSTAD RGPH-3

Livré le 8 nov. 2026, à la demande de Robleh : intégrer les nouvelles images
(BCD 2024 et INSTAD RGPH-3) dans l'app React, après confirmation que les
7 thèmes P-028 sont bien intégrés au template.

## Confirmation thèmes (P-028, vérifié le 8 nov. 2026)

Oui, les 7 nuances sont intégrées dans le template, source de vérité
`src/lib/theme.ts` : Violet / Vert (défaut), Teal / Ocre (Djibouti),
Océan, Forêt, Coucher de soleil, Prune / Rose, Clair (institutionnel).
Sélecteur en topbar, pastilles + noms, aperçu immédiat, choix mémorisé
`localStorage` clé `mizan_theme_mode`, mode Auto par défaut (Djibouti =
Teal/Ocre, Canada = Violet/Vert). `colorForValue()` + `scaleFor()` : rampe
choroplèthe, accent dashboard et KPI calculés sur les valeurs affichées,
dans le thème choisi. La page P-033 utilise `currentTheme()` : fond,
surfaces, KPI et barres suivent le thème choisi, sans changer les chiffres.

## Données (réelles, snapshot local du 8 nov. 2026)

### BCD — Rapport Annuel 2024
Source : https://banque-centrale.dj/wp-content/uploads/2025/09/Rapport-Annuel_-V.Definitive.pdf
Valeurs extraites de la Synthèse (p. 2-3). Aucune valeur inventée.

- Croissance PIB réel : 6,8 % en 2024 contre 7,4 % en 2023 ; perspectives ~7 % en 2025-2028.
- Inflation moyenne : 2,1 % contre 1,5 %.
- Recettes publiques : 137,5 Mds FDJ, +9,4 % ; dépenses 157,1 Mds ; déficit -2,5 % du PIB contre -3,4 %.
- Compte courant : excédent 110,4 Mds contre 125,8, -14,6 %.
- Dette publique extérieure : 508,9 Mds contre 487,5, +4,4 % ; service 27,183 Mds (principal 19,176, intérêts 8,008).
- Masse monétaire : 524,7 Mds contre 507,4, +3,4 %.
- Bilan des banques : 668,7 Mds contre 637,3, +4,9 %.
- Crédits à la clientèle : 287,7 Mds contre 212,4, +35,4 %, part 43 % contre 33 %.
- Dépôts : 487,3 Mds contre 470,4, +3,6 %.
- Fonds propres : 52,3 Mds, +10,4 % ; solvabilité 21 % contre 19,4 %, minimum 12 % ; créances en souffrance 3,54 % contre 4,18 %.
- Monnaie électronique : 142 681 comptes actifs contre 69 133 ; 14 876 739 transactions, valeur 73,1 Mds FDJ contre 3 461 524 et 53,4 Mds en 2023.

### INSTAD — RGPH-3
Source : INSTAD, RGPH-3, résultats provisoires août 2024, définitifs juin 2025.

- Population : 1 066 809 au 20 mai 2024 contre 818 159 en 2009, +1,8 % par an.
- Djibouti-Ville : 767 250 habitants, 71,9 % en définitif, 72,8 % en provisoire (écart signalé dans la page, chiffre définitif retenu).
- Âge moyen 25,6 ans, médian 22,9 ans. Ménages 174 658, taille moyenne 6, urbain 84,3 %.
- Femmes 536 447, hommes 530 362.

## Livré

- `src/data/bcd/bcd_2024.json` (16 KPI, 2023 et 2024), `src/data/instad/rgph3.json`
- `src/lib/bcd.ts` (accès typé, attributions)
- `src/pages/Bcd.tsx` (page `bcd`) : 8 KPI BCD, graphique en barres 2023 vs 2024, solidité bancaire et monnaie électronique, 4 KPI RGPH-3 + repères. **Aucune carte** : à la demande de Robleh, la cartographie a été retirée des images BCD et INSTAD, elle ne ressemblait pas à Djibouti.
- Navigation : entrée `bcd` dans `App.tsx`, carte sur l'accueil (`Home.tsx`), clés i18n `bcd*` FR/EN/AR.
- Séries séparées : BIE (2001-2012), BCD/RGPH-3, dashboard INSTAD démo, Canada StatCan. Aucun mélange.

## Vérification

`npm run build` OK, preview HTTP 200. Aucune clé en dur, aucun appel réseau.

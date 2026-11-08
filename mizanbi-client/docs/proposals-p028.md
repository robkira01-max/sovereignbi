# P-028 — Bibliothèque de thèmes, pilotée par les données et la cartographie

Date : 7 novembre 2026. Fichier moteur : `src/lib/theme.ts`.
Projet à vocation commerciale : l'utilisateur choisit son thème, et le thème
« prend vie » avec les données.

## La bibliothèque : 7 thèmes

Chaque thème a sa palette complète : fond, cartes, bordures, brand, accent,
accent 2 (`--accent-soft`), avertissement, danger, texte, texte secondaire,
halos, rampe carte bas/moyen/haut, couleur de graphique.

| # | Thème | Brand | Accent | Rampe carte |
|---|---|---|---|---|
| 1 | Violet / Vert (par défaut) | violet `oklch(65% 0.22 265)` | vert `oklch(68% 0.18 155)` | violet → bleu → vert |
| 2 | Teal / Ocre — Djibouti | teal `oklch(62% 0.16 190)` | ocre `oklch(72% 0.18 55)` | teal → vert → orange |
| 3 | Océan | bleu `oklch(60% 0.18 240)` | cyan `oklch(68% 0.15 195)` | bleu → bleu → cyan |
| 4 | Forêt | vert profond `oklch(55% 0.16 150)` | vert clair `oklch(70% 0.18 130)` | vert sombre → vert → vert clair |
| 5 | Coucher de soleil | ambre `oklch(65% 0.2 55)` | corail `oklch(62% 0.22 25)` | ambre → orange → corail |
| 6 | Prune / Rose | prune `oklch(60% 0.2 320)` | rose `oklch(68% 0.18 10)` | prune → magenta → rose |
| 7 | Clair — démo institutionnelle | violet sombre `oklch(50% 0.22 265)` | vert sombre `oklch(48% 0.16 155)` | violet clair → bleu → vert sombre |

Variables CSS pilotées : `--bg, --surface, --surface-solid, --border, --brand,
--brand-hover, --accent, --accent-soft, --warning, --danger, --text, --muted,
--muted-2, --glow-1/2/3, --map-low, --map-mid, --map-high, --indicator-accent,
--chart`. Elles sont posées sur `:root` par `applyTheme()` ; `index.css` ne
contient que les valeurs par défaut (Violet/Vert). Les surfaces structurelles
(sidebar, topbar, tableaux, formulaires) et les textes secondaires utilisent
ces variables, pas des couleurs codées en dur — c'est ce qui rend le thème
Clair possible.

## Sélecteur (topbar)

Menu avec pastilles de couleur + nom de chaque thème, aperçu immédiat
(le thème s'applique dès le clic, sans rechargement, transition douce 0,45 s),
choix mémorisé en `localStorage` (`mizan_theme_mode`).

Mode **Auto** (par défaut) : le thème suit le jeu de données — Djibouti =
Teal/Ocre, Canada = Violet/Vert, accueil = Violet/Vert neutre. Dès que
l'utilisateur choisit un thème, son choix prime sur la page, partout.

## Le thème « prend vie » avec les données

- `scaleFor(valeurs, thème, unité)` : min/max **réels** des valeurs affichées
  + quartiles (Q1, médiane, Q3). Aucun seuil codé en dur par région.
- `colorForValue(valeur, échelle)` : interpolation oklch bas → milieu → haut,
  dans la rampe **du thème choisi**. Changer de thème ne change jamais les
  chiffres, seulement les couleurs.
- L'accent du dashboard change avec l'indicateur (`--indicator-accent`) :
  chômage → rouge/danger, pauvreté et IPC → ambre, population → brand.
- Légende dynamique : bornes min/max réelles, médiane, quartiles, et seuil de
  référence propre au jeu de données — Djibouti : alerte chômage 25 %
  (démo, 2024) ; Canada : référence nationale 6,7 % (oct. 2026, réel).
  La référence est passée à `scaleFor()` en option, elle ne dépend pas du thème.
- Indicateurs : SIG Djibouti — chômage / population / pauvreté ;
  page Canada — chômage / population / IPC (l'IPC n'a pas de ventilation
  provinciale dans le snapshot : la carte reste alors sur le chômage, et
  c'est écrit sur la page).
- Mode bivarié pauvreté × chômage (P-025) préservé tel quel dans `Sig.tsx`.
- Tuiles choroplèthes (`TileRenderer`), quartiers de Djibouti-ville et carte
  ADM1 (`DjiboutiMap`) utilisent la même fonction `colorForValue()`.
- Les ticks et infobulles des graphiques Recharts lisent aussi le thème
  courant (`currentTheme()`), pour rester lisibles en thème Clair.

## Accessibilité

La couleur seule n'informe jamais : chaque région / province / cellule porte
son nom **et** sa valeur, et la légende affiche les valeurs numériques.
`textOnFill()` choisit le texte blanc ou sombre (`#070711`) selon la clarté
réelle du remplissage (oklch > 58 % → texte sombre), ce qui vaut pour les
7 thèmes, thème Clair compris (sa rampe basse est claire : texte sombre sur
les zones basses). Vérifié pour chaque thème : texte principal, texte
secondaire (`--muted` / `--muted-2`), KPI (`--accent-soft`, sombre en thème
Clair), boutons actifs (texte blanc sur `--brand`), libellés de carte
(blanc avec ombre portée sur remplissage sombre, sombre avec halo clair sur
remplissage clair).

## Données — aucune valeur inventée

Djibouti démo : population 1 030 000, chômage pondéré 23,5 %, 6 régions
(22,3 % à 29,1 %). Canada réel : snapshot StatCan du 7 nov. 2026
(chômage 6,7 % oct. 2026, population 41 798 407, IPC 170,0).

## Ajouter un 8e thème

1. Ajouter une entrée à `THEMES` dans `src/lib/theme.ts` (`ThemeId`,
   variables CSS complètes, rampe `mapLow/Mid/High`, couleur de graphique,
   pastilles `swatch`) — ne coder de couleur nulle part ailleurs.
2. L'ajouter à `THEME_LIST` (ordre d'affichage du menu). Le sélecteur,
   la persistance et l'aperçu immédiat fonctionnent sans autre changement.
3. Vérifier le contraste : texte sur fond, texte secondaire, KPI
   (`--accent-soft`), boutons actifs, libellés de carte via `textOnFill()`,
   en particulier si la rampe est claire.
4. Relancer `npm run build` et vérifier le thème Clair et le nouveau thème
   sur les pages Accueil, SIG et Canada.

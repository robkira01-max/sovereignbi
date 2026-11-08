# Palette des thèmes MizanBI — P-028

Sauvegardée le 7 novembre 2026, à la demande de Robleh.
Source de vérité du code : `src/lib/theme.ts`. Ce fichier est la référence lisible.

Chaque thème a : fond, brand, accent, rampe carte bas → milieu → haut, couleur de graphique.
Alerte partout : jaune `oklch(72% 0.19 55)`, danger `oklch(58% 0.22 25)`
(sauf Coucher de soleil et Clair, danger ajusté pour le contraste).
La carte interpole bas → milieu → haut selon la valeur affichée, jamais de couleur fixe par région.
Références de légende propres au jeu de données : alerte 25 % Djibouti, 6,7 % Canada.

## 1. Violet / Vert — par défaut, Canada en mode Auto
- Fond : `#070711`
- Brand : `oklch(65% 0.22 265)` — Accent : `oklch(68% 0.18 155)`
- Carte : `oklch(34% 0.14 265)` → `oklch(50% 0.16 200)` → `oklch(64% 0.18 155)`
- Graphique : `#34d399`

## 2. Teal / Ocre — Djibouti, en mode Auto
- Fond : `#08110f`
- Brand : `oklch(62% 0.16 190)` — Accent : `oklch(72% 0.18 55)`
- Carte : `oklch(38% 0.12 190)` → `oklch(52% 0.14 120)` → `oklch(58% 0.2 25)`
- Graphique : `#2dd4bf`

## 3. Océan
- Fond : `#060d18`
- Brand : `oklch(60% 0.18 240)` — Accent : `oklch(68% 0.15 195)`
- Carte : `oklch(36% 0.13 245)` → `oklch(52% 0.16 225)` → `oklch(66% 0.16 195)`
- Graphique : `#38bdf8`

## 4. Forêt
- Fond : `#071009`
- Brand : `oklch(55% 0.16 150)` — Accent : `oklch(70% 0.18 130)`
- Carte : `oklch(32% 0.11 155)` → `oklch(48% 0.15 145)` → `oklch(64% 0.18 125)`
- Graphique : `#4ade80`

## 5. Coucher de soleil
- Fond : `#120a08`
- Brand : `oklch(65% 0.2 55)` — Accent : `oklch(62% 0.22 25)`
- Carte : `oklch(40% 0.14 60)` → `oklch(55% 0.18 40)` → `oklch(60% 0.2 20)`
- Graphique : `#fb923c`

## 6. Prune / Rose
- Fond : `#110710`
- Brand : `oklch(60% 0.2 320)` — Accent : `oklch(68% 0.18 10)`
- Carte : `oklch(36% 0.14 320)` → `oklch(52% 0.16 340)` → `oklch(62% 0.18 5)`
- Graphique : `#f472b6`

## 7. Clair — démo institutionnelle
- Fond : `#f4f2ee`
- Brand : `oklch(50% 0.22 265)` — Accent : `oklch(48% 0.16 155)`
- Carte : `oklch(72% 0.1 265)` → `oklch(55% 0.16 230)` → `oklch(40% 0.18 155)`
- Graphique : `#059669`

## Mode Auto
- Djibouti → Teal / Ocre, Canada → Violet / Vert, accueil → Violet / Vert.
- Dès que l'utilisateur choisit un thème, son choix prime et est mémorisé (`localStorage`, clé `mizan_theme_mode`).

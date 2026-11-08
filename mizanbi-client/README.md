# MizanBI — application React

BI conversationnelle auto-hébergée, hors ligne et souveraine, pour l'INSTAD Djibouti.
Portage en **React 18 + Vite + TypeScript** du prototype Claude Design
`MizanBI.dc.html` (téléversé le 7 novembre 2026, dossier `design_handoff_mizanbi`).

Slogan : « L'IA vient à vos données, pas l'inverse. »
Conformité : **Loi 25 / LPRPDE**.

## Démarrage

```bash
npm install
npm run dev      # http://localhost:5173
npm run build    # sortie : dist/
npm run preview  # sert dist/ en local
```

## Déploiement Vercel

- Build command : `npm run build`
- Output directory : `dist`
- Variable d'environnement : `VITE_API_BASE` (voir `.env.example`).
  Laisser vide = mode démo, aucune requête réseau.
  Exemple : `VITE_API_BASE=https://sovereignbi-api.147-5-126-188.sslip.io`

**Sécurité : aucune clé API, aucun token, aucun mot de passe en dur dans le code
ni dans `.env`.** L'authentification se fait par `POST /auth/login`, le token est
stocké en `localStorage` (`mizan_token`, `mizan_email`). Les en-têtes
`X-Api-Key: viewer|editor` ne sont envoyés que si une clé est fournie au runtime
(par l'administrateur, jamais commitée).

## Propositions P-022 à P-028 (7 novembre 2026)

Détail : `docs/proposals-p022-p026.md`, `docs/proposals-p027.md` et `docs/proposals-p028.md`.

- **P-022 Agent BI** : suites logiques cliquables, 2e vérification affichée,
  alerte démo (Obock 29,1 %, seuil 25 % dépassé), SQL visible, aucune précision affirmée.
- **P-023 Preuve de confiance** : provenance + SQL + score sous chaque tuile
  et chaque réponse, état « Je m'abstiens » hors périmètre, page Certificat de précision.
- **P-024 Digests proactifs** : section Bulletins, bulletin hebdomadaire démo
  (semaine du 3 nov. 2026), chaque lundi, sans envoi réel en démo, export HTML offline.
- **P-025 Offline + MizanSIG unifié** : badge Hors ligne, polices système
  uniquement (Google Fonts retiré : aucun CDN externe), PWA / collecte terrain
  à venir, flux illustratifs masqués par défaut (Comtrade réel à brancher, clé backend).
- **P-026 Gel pilote + modèle commercial** : aucune nouvelle fonctionnalité
  avant le pilote INSTAD (sauf P-022/P-023) ; licence annuelle par installation,
  sans quota de questions, sans cloud obligatoire. Aucun compteur ni paywall.
- **P-027 Connecteur Statistique Canada (WDS)** : 3 tables réelles vérifiées
  en direct (voir section ci-dessous), snapshot local du 7 nov. 2026,
  page Canada séparée du dashboard INSTAD. Aucune clé, aucun appel réseau
  en mode démo.
- **P-028 Bibliothèque de thèmes** : 7 thèmes nommés (Violet/Vert par
  défaut, Teal/Ocre Djibouti, Océan, Forêt, Coucher de soleil, Prune/Rose,
  Clair pour la démo institutionnelle), sélecteur à pastilles en topbar
  avec aperçu immédiat et choix mémorisé, mode Auto qui suit le jeu de
  données (Djibouti = Teal/Ocre, Canada = Violet/Vert) jusqu'au choix
  manuel. Rampe choroplèthe, accent et KPI calculés sur les valeurs
  affichées dans le thème choisi (`colorForValue`, échelle min/max +
  quartiles, légende dynamique) ; changer de thème ne change jamais les
  chiffres. Accessibilité : valeur sur chaque zone, texte sombre sur
  remplissage clair. Détail : `docs/proposals-p028.md`.
- **P-029 Cartes anciennes scannées** : import JPG/PNG/WebP/PDF (rendu PDF
  local via pdfjs-dist, worker embarqué, aucune dépendance CDN), géoréférencement
  par points de contrôle (affine, 3 points exacts, 4+ par moindres carrés,
  erreur résiduelle en km), aperçu superposé avec opacité et zoom, fiche
  (titre, année, source, zone, échelle, notes), sauvegarde locale, exemple
  démo inclus. Le scan est affiché tel quel : rien n'est retracé. Limites :
  l'affine ne corrige pas les déformations du papier ; carte de référence
  Djibouti ADM1 uniquement pour l'instant. Détail : `docs/proposals-p029.md`.
- **P-030 BIE, Ministère des Finances de Djibouti** : analyses MizanBI des
  Bulletins d'information économique et Notes de conjoncture 2001-2012
  (page https://www.ministere-finances.dj/BIE.html), snapshot local du
  8 nov. 2026 (`src/data/bie/`, 74 valeurs, 35 documents listés, 22
  accessibles). Évolution par indicateur (croissance PIB 0,4 % en 2000 →
  5,8 % en 2008, dette 47,6 → 100,9 Mds FD), variations d'année en année,
  tableau récapitulatif, analyse en 8 points, partie Prévisions séparée
  (tendance linéaire MizanBI, horizon 2009-2012, intervalle ; prévisions du
  ministère affichées à part). 2001-2004 inaccessibles (cadres, fichiers
  vides), 2009 sans total annuel, 2012 partiel (janv.-sept.). Détail :
  `docs/proposals-p030.md`.
- **P-033 BCD 2024 + INSTAD RGPH-3** : Banque Centrale, Rapport Annuel 2024
  (croissance 6,8 %, inflation 2,1 %, masse monétaire 524,7 Mds FDJ,
  dette extérieure 508,9 Mds FDJ, crédits +35,4 %) et INSTAD RGPH-3
  (population 1 066 809 en 2024, Djibouti-Ville 767 250, 71,9 % en
  définitif). Page `Bcd.tsx`, graphiques en barres 2023 vs 2024, aucune
  carte, à la demande de Robleh. Détail : `docs/proposals-p033.md`.
- **P-031 Tableau de bord national Canada, d'après la maquette** : mise en page
  de la maquette conservée (onglets, navigation latérale, 3 KPI, emploi par
  province, carte du Canada, tranches d'âge), mais les chiffres de la maquette
  ont été VÉRIFIÉS via le WDS (table 14-10-0287-01, snapshot emploi du
  8 nov. 2026) et la plupart étaient faux : chômage +0,2 pt (et non −0,3 pt),
  population +0,5 % (et non +0,8 %), emploi −4 700 (et non +12 450), tranches
  d'âge 12,6 % / 66,8 % / 20,5 % (et non 9,2 % / 68,5 % / 22,3 %), plus forte
  hausse C.-B. +12 300 et plus forte baisse Alberta −24 300 (et non Québec /
  Alberta +4,2 %). Les écarts sont listés dans la page. Contours simplifiés
  du Canada (`src/data/ca_provinces.json`, Click That Hood, données ouvertes).
  Détail : `docs/proposals-p031.md`.

## BIE Djibouti (P-030) — données réelles du ministère, snapshot local

Détail : `docs/proposals-p030.md`. Page `Bie.tsx`, accessible depuis l'Accueil
et la sidebar, thème courant P-028. Données réelles, séparées des chiffres démo
Djibouti (1 030 000 hab. / 23,5 %) et du template Canada : aucune série ne
mélange les trois. Chaque valeur porte sa source exacte (document, URL, page).
Les années manquantes ne sont jamais interpolées. Les prévisions sont celles
du modèle MizanBI (tendance linéaire, intervalle ±1,96 × écart-type résiduel),
jamais présentées comme des données du ministère.

## Statistique Canada (P-027) — données réelles, snapshot local

Détail : `docs/statcan-p027.md`. Licence ouverte de Statistique Canada :
usage commercial permis, sans frais, avec attribution obligatoire
« Source : Statistique Canada, [nom du produit], [date de référence] ».

Tables vérifiées en direct via le Web Data Service (WDS), téléchargées
le 7 novembre 2026, snapshot local dans `src/data/statcan/` (16 Ko) :

| Table | Contenu | Référence |
|---|---|---|
| 14-10-0287-01 | Chômage mensuel par province, désaisonnalisé | oct. 2026, Canada 6,7 % |
| 17-10-0009-01 | Population trimestrielle, 1er juillet | 1er juill. 2026, Canada 41 798 407 |
| 18-10-0004-01 | IPC mensuel, ensemble, 2002 = 100 | sept. 2026, 170,0 (+3,1 % sur un an) |

La page **Canada** (`src/pages/Canada.tsx`, accessible depuis l'Accueil
et la sidebar) affiche ces chiffres avec leur provenance complète sur
chaque tuile. La page **Tableau de bord national — Canada**
(`src/pages/CanadaNational.tsx`, P-031) reprend la mise en page de la
maquette fournie par Robleh, avec l'emploi vérifié sept. → oct. 2026
(snapshot `src/data/statcan/statcan_emploi.json`, téléchargé le 8 nov. 2026)
et un tableau des corrections par rapport à la maquette.
chaque tuile. Les chiffres canadiens ne sont **jamais** mélangés aux
chiffres démo de Djibouti (1 030 000 hab. / 23,5 %).

**Rafraîchir le snapshot** (à faire quand les données datent) :
```bash
# 1. Vérifier l'ID et la date de publication (métadonnées WDS)
curl -X POST -H "Content-Type: application/json" \
  -d '[{"productId": 14100287}]' \
  https://www150.statcan.gc.ca/t1/wds/rest/getCubeMetadata
# 2. Télécharger le CSV complet
curl "https://www150.statcan.gc.ca/t1/wds/rest/getFullTableDownloadCSV/14100287/en"
#    → lien ZIP dans le champ "object", puis décompresser
# 3. Extraire en streaming (CSV de l'EPA : 1,18 Go décompressé — ne pas
#    le charger en entier) les lignes Canada + 10 provinces, dernières
#    périodes, et réécrire src/data/statcan/*.json + statcan_sources.json
#    (product_id, nom exact, date de référence, date de téléchargement).
# 4. Supprimer les CSV bruts volumineux, puis npm run build pour vérifier.
# L'accès live optionnel (src/lib/statcan.ts, fetchStatCanTable) exige
# VITE_STATCAN_LIVE=1 et n'est jamais appelé par l'interface.
```

## Pages (5 + 3)

1. **Login** (`/`, état) : carte 400 px, logo M dégradé violet → vert, email /
   mot de passe, Connexion (`POST /auth/login`), « Explorer en mode démo ».
2. **Accueil Bento** : grille 4 colonnes, max 1000 px. Carte réelle de Djibouti
   (6 régions ADM1, GeoJSON geoBoundaries embarqué dans `src/data/dj_adm1.json`),
   courbe chômage 2009 → 2024, 2 KPI, tuile Prévisions 2030, tuile Tables chargées
   (`GET /api/v1/health` → `tables`, repli démo si l'API est hors ligne).
3. **Q&A** : bascule Données / Général, messages, badge confiance
   (vert / ambre / rouge), bloc SQL repliable avec bouton Copier, tableau compact,
   champ sticky, suggestions. `POST /api/v1/chatbot` (repli `/ask`) avec
   historique de 10 tours, repli démo si l'API est injoignable.
4. **Dashboards** : liste (`GET /dashboards`) puis détail avec tuiles
   kpi / bar / line / pie / table / choropleth / grid, bouton « ↓ Bulletin »
   (`GET /dashboards/{id}/export/bulletin`, blob).
5. **Import** : drag & drop CSV / XLSX, `POST /upload` multipart
   (en-tête editor), liste des tables créées. En mode démo, le nom de table est
   dérivé du nom de fichier, sans envoi réseau.
6. **Bulletins** (P-024) et **Certificat de précision** (P-023) : accessibles
   depuis l'Accueil et la sidebar.
7. **Canada** (P-027) : template Statistique Canada, données réelles
   (snapshot 7 nov. 2026), accessible depuis l'Accueil et la sidebar,
   séparé du dashboard INSTAD.
8. **BIE** (P-030) : analyses des bulletins du Ministère des Finances de
   Djibouti 2001-2012, données réelles (snapshot 8 nov. 2026), évolution +
   prévisions séparées, accessible depuis l'Accueil et la sidebar.

**Hors ligne (P-025) :** aucune police Google, aucune tuile en ligne, aucun CDN
externe. Polices système uniquement. En mode démo, aucune requête réseau.

Langues : **FR / EN / AR** (sélecteur en topbar et sur le login, `dir="rtl"` pour AR,
graphiques forcés `dir="ltr"`).

## Structure en 2 volets (décision de Robleh)

- **Volet 1 — Analyse BI / Dashboard** : Accueil, Q&A, Dashboards, Import.
- **Volet 2 — Cartographie SIG** : carte interactive Djibouti ADM1 / ADM2 /
  quartiers (11 quartiers de Djibouti-ville), choroplèthe, choroplèthe bivariée
  pauvreté × chômage, flux Djibouti → Éthiopie, fond offline PMTiles mentionné.
- Sélecteur en topbar : Vue d'ensemble / BI / SIG.
- **Bulle flottante ChatBI** (56 px, bas-droite, dégradé violet) sur toutes les
  pages sauf Q&A, elle ouvre le Q&A.
- Layout du handoff : sidebar 60 px (icônes 42 × 42), topbar 56 px, `main` 28 px,
  fond `#070711` + 3 radial-gradient, surface `oklch(13% 0.025 265 / .85)`,
  brand `oklch(65% 0.22 265)`, accent vert `oklch(68% 0.18 155)`,
  Instrument Sans / JetBrains Mono (SQL), radius 16–18 px.

## Données de démonstration — chiffres cohérents

Chaque écran porte le badge **« Données : Démo »**.

- Population totale : **1 030 000** = somme exacte des 6 régions
  (Djibouti-ville 745 300, Ali Sabieh 91 800, Dikhil 72 400, Tadjourah 67 100,
  Obock 28 500, Arta 24 900).
- Chômage national pondéré : **23,5 %**
  (somme population × taux / 1 030 000 = 23,4999 %).
  Par région : Djibouti-ville 22,3 %, Ali Sabieh 24,6 %, Dikhil 28,4 %,
  Tadjourah 27,1 %, Obock 29,1 %, Arta 25,0 %.
- Tendance : 28,9 % (2009) → 23,5 % (2024). Prévisions 2030 : 23,1 %,
  IC 20,5 – 26,0 (projection indicative, tendance linéaire — reprise du prototype).

### Écart avec le prototype — à ne pas réintroduire

Le prototype Claude Design affichait **26,8 %** de chômage moyen et
**1 062 000** habitants (Obock 33,2 %, Dikhil 31,5 %, Ali Sabieh 22,3 %).
Ces valeurs contredisent les totaux et les autres écrans : elles ne sont
**pas reprises** dans cette application. Le vrai taux doit venir de Robleh
ou de l'INSTAD ; en attendant, les chiffres ci-dessus sont les seuls utilisés,
partout, et marqués Démo.

Les 11 quartiers de Djibouti-ville sont **approximatifs** (positions
schématiques, pas des contours officiels) — à valider avec la mairie.
Les flux commerciaux sont des valeurs **illustratives** ; les vraies valeurs
viennent du connecteur UN Comtrade Plus (P-020) quand la clé est configurée.

## Arborescence

```
src/
  main.tsx            # QueryClient TanStack Query + App
  App.tsx             # auth, langue, routing par état, sidebar/topbar, bulle ChatBI
  index.css           # tokens du handoff (oklch, radius, bento, chat)
  data/
    demo.ts           # régions, KPI, dashboards démo, quartiers, flux
    dj_adm1.json   # contours ADM1 geoBoundaries (licence ouverte), embarqué
    statcan/          # P-027 : snapshot StatCan 7 nov. 2026 (4 JSON, 16 Ko)
    bie/              # P-030 : snapshot BIE 8 nov. 2026 (2 JSON, 42 Ko, 74 valeurs)
  lib/
    api.ts            # VITE_API_BASE, login, chat, headers (aucune clé en dur)
    statcan.ts        # P-027 : lecture snapshot local, WDS live opt-in (VITE_STATCAN_LIVE=1)
    geo.ts            # projection équirectangulaire cos(lat) du GeoJSON
    i18n.ts           # dictionnaires FR/EN/AR
  components/
    DjiboutiMap.tsx   # carte SVG ADM1 + légende + sélection de région
    TileRenderer.tsx  # tuiles kpi/bar/line/pie/table/choropleth/grid (Recharts)
  pages/
    Login.tsx  Home.tsx  Chat.tsx  Dashboards.tsx  Import.tsx  Sig.tsx
    Bulletins.tsx  Certificate.tsx  Canada.tsx  # P-027
    AncientMaps.tsx  # P-029 : cartes anciennes scannées, géoréférencement
    Bie.tsx  # P-030 : analyses BIE, évolution + prévisions
```

## Ce qui reste à brancher sur la vraie API

- `VITE_API_BASE` : définir l'URL de l'API SovereignBI (voir `.env.example`).
- Vérifier la forme exacte des réponses `/dashboards` et `/dashboards/{id}`
  (liste ou `{dashboards}`, tuiles `[{id, type, title}]`) — le handoff signale
  ce point comme à confirmer.
- Brancher les chiffres de l'Accueil (KPI, prévisions) sur de vrais endpoints ;
  aujourd'hui ils viennent de `src/data/demo.ts`.
- Contours ADM2 (`data/geo/dj_adm2.geojson` côté backend) pour remplacer la
  vue tabulaire ADM2 par une vraie carte.
- Clé UN Comtrade Plus (`COMTRADE_API_KEY`, côté backend uniquement) pour
  remplacer les flux illustratifs par les vraies valeurs.
- Le fichier `uploads/CLAUDE (1).md` du zip (Mon Garage / Tucson 2022) est
  un autre projet, sans rapport : il a été **ignoré** et n'est inclus nulle part.

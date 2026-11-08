# P-029 — Import de cartes anciennes scannées

Livré le 7 novembre 2026, dans l'app React uniquement (`src/pages/AncientMaps.tsx`,
`src/lib/ancientMaps.ts`, helpers de projection dans `src/lib/geo.ts`).

## Principe

Robleh a beaucoup de cartes papier anciennes scannées (JPG/PNG/WebP/PDF). Au lieu
de redessiner les cartes, l'outil **géoréférence le scan** : l'utilisateur place
des points de contrôle (un repère sur le scan + ses coordonnées lon/lat), une
transformation affine cale le scan sur la carte de référence, et le scan est
affiché tel quel, en couche par-dessus. **Rien n'est retracé** : les contours
d'origine sont préservés, avec le badge « Carte ancienne — scan, non retracée ».

## Fonctionnement

1. **Import** : drag & drop ou choix de fichier. Images JPG/PNG/WebP, et PDF
   (rendu en image avec pdf.js, embarqué localement — aucune dépendance CDN,
   aucun envoi serveur). Pour un PDF de plusieurs pages, l'utilisateur choisit
   la page à caler ; seule cette page est rendue. L'image est compressée
   (JPEG, max 1600 px) pour tenir dans le stockage local.
2. **Points de contrôle** : clic sur le scan (repère en pixels), puis clic sur
   la carte de référence Djibouti ADM1 (conversion en lon/lat), ou bouton
   ville prédéfinie (Djibouti-ville, Tadjourah, Obock, Ali Sabieh, Dikhil,
   Arta), ou saisie directe lon/lat. Chaque point est modifiable (replacer sur
   le scan / sur la carte) ou supprimable.
3. **Calcul** : transformation affine. 3 points = solution exacte ; 4+ points =
   moindres carrés. Erreur résiduelle par point en km (approx., 111 km/degré),
   RMS et max affichés. Avertissement si les points sont presque alignés
   (aire du triangle < 1 % de l'emprise) ou si la transformation est dégénérée.
4. **Aperçu superposé** : scan géoréférencé en `<image>` SVG avec la matrice
   affine composée avec la projection de la carte de référence. Curseur
   d'opacité, bascule Superposition / Scan seul / Carte seule, zoom ×1 à ×4.
5. **Fiche** : titre, année, source/auteur, zone, échelle, notes. Sauvegarde
   locale (localStorage : métadonnées + points + image compressée), liste des
   cartes avec ouvrir / exporter la fiche en JSON / supprimer.
6. **Exemple démo** : un schéma fictif (pas une vraie carte ancienne) avec
   3 repères fictifs sur Djibouti-ville, Tadjourah et Obock, pour tester le
   calage sans scan.

## Limites (à dire à l'utilisateur)

- L'**affine ne corrige pas** les déformations du papier (pli, scan tordu) ni
  les projections anciennes très différentes de la projection actuelle. Pour
  une carte très déformée, il faudrait un géoréférencement par plaque fine
  (thin plate spline) — hors périmètre de P-029.
- **4+ points bien répartis** (quatre coins) fortement conseillés ; 3 points
  alignés donnent un calage non fiable (avertissement affiché).
- **Carte de référence = Djibouti ADM1 uniquement** pour l'instant. Pour une
  carte du Canada ou d'ailleurs, on peut saisir les lon/lat manuellement, mais
  l'aperçu superposé reste sur le fond Djibouti ; une carte de référence Canada
  (limites ouvertes StatCan) est une suite possible.
- **PDF multi-pages** : une seule page à la fois est calée.
- **Stockage local** : localStorage (~5 Mo par navigateur). Si l'image est
  trop lourde, la fiche est gardée sans l'image et il faut réimporter le scan.
- Les erreurs résiduelles sont des approximations (111 km/degré, longitude
  corrigée par cos(latitude moyenne)) : elles servent à repérer un point mal
  placé, pas à certifier une précision métrique.

## Fichiers

- `src/lib/ancientMaps.ts` : types, `fitAffine` (moindres carrés), compression,
  rendu PDF (pdfjs-dist, worker local), stockage localStorage, carte démo.
- `src/lib/geo.ts` : `projectLonLat`, `unprojectView`, `djiboutiBounds`,
  `inDjiboutiBounds` (mêmes formules que `buildDjiboutiMap`).
- `src/pages/AncientMaps.tsx` : import, calage, aperçu, bibliothèque.
- `src/App.tsx` : page `ancient` dans la navigation (icône couches).
- `src/pages/Sig.tsx` : bouton « Cartes anciennes — importer un scan ».
- `src/lib/i18n.ts` : clés `ancientMaps`, `ancientMapsSub`, `ancientBadge`
  (FR/EN/AR).

## Comment ajouter une 8e carte de référence

Ajouter le GeoJSON ADM1 du pays dans `src/data/`, une fonction de projection
équivalente dans `src/lib/geo.ts`, et un sélecteur de fond dans
`AncientMaps.tsx` (la matrice affine est composée avec la projection du fond
choisi).

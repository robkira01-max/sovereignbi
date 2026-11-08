# P-030 — BIE, Ministère des Finances de Djibouti : analyses MizanBI

## Source
Page : https://www.ministere-finances.dj/BIE.html — « Bulletin d'information économique »,
téléchargée le 8 novembre 2026. 35 liens listés, 22 documents accessibles (PDF),
les PDF bruts restent dans /tmp (hors dépôt) ; seul le snapshot JSON léger est
embarqué : `src/data/bie/bie_series.json` (74 valeurs) et `src/data/bie/bie_sources.json`.

## Couverture par année
| Année | Statut | Détail |
|---|---|---|
| 2001 | ❌ Inaccessible | 3 liens .htm : pages à cadres (frameset), contenu non récupérable. |
| 2002 | ❌ Inaccessible | 3 liens : 1 fichier vide (0 octet), 2 pages à cadres. |
| 2003 | ❌ Inaccessible | 3 liens : pages à cadres. |
| 2004 | ❌ Inaccessible | 3 liens : 2 fichiers vides, 1 page à cadres (T4). |
| 2005 | ✅ Accessible | BIE 2005 def.pdf, 67 p. Le .mht « LR 2005 » est une loi rectificative, pas un BIE. |
| 2006 | ✅ Accessible | BIE 2006.pdf, 117 p. Second fichier « BIE version finale.pdf » (102 p.), même contenu, non retenu comme source principale. |
| 2007 | ✅ Accessible | BIE 2007 avec graphiques1 definitif 2.pdf, 82 p. Le lien « BIE 2007.pdf » renvoie 404. |
| 2008 | ✅ Accessible | BIE 2008 Finale.pdf, 87 p. (lien en double, même fichier). |
| 2009 | ⚠ Partiel | Notes T1 (18 p.), T2 (27 p.), T3 (23 p.) ; note T4 absente — pas de total annuel. |
| 2010 | ✅ Accessible | Notes T1 (26 p.), T2 (26 p.), T3 (29 p.), T4 (31 p.). |
| 2011 | ✅ Accessible | Notes T1 (30 p.), T2 (37 p.), T3 (32 p.), T4 (31 p.). |
| 2012 | ⚠ Partiel | Notes T1 (31 p.), T2 (32 p.), T3 (28 p.) ; note T4 absente (lien « trimestre 2012 _VF.PDF » inaccessible) — pas de total annuel. |

## Méthode
- Extraction du texte des PDF par `pdftotext -layout`, lecture des tableaux
  de synthèse (Tableau 1 du BIE 2005, Tableau 3 du BIE 2006, Tableau 8 du BIE 2007,
  TOFE et dette du BIE 2008, Tableaux 18-19 de la note T4 2011, Tableau 12 de la
  note T4 2010).
- Dernière vintage par année : quand deux bulletins diffèrent pour la même année,
  la valeur du bulletin le plus récent est retenue et l'écart est signalé dans la
  source. Exemples : croissance 2006, 4,5 % (provisoire, BIE 2006) puis 4,8 %
  (BIE 2007) ; recettes 2005, 43 454 (BIE 2005) puis 46 711 (BIE 2006) ; dette 2005,
  67 632 (BIE 2005) puis 68 231 (BIE 2008) ; investissement 2006, 30,1 % puis 35,0 %.
- Les valeurs 2008-2010 des tableaux prospectifs du BIE 2007 sont des prévisions
  du ministère, marquées `prevision_ministere`, jamais du réalisé.
- Les années manquantes ne sont jamais interpolées : la courbe se coupe.
- Aucune valeur devinée : ce qui est illisible ou absent est marqué manquant.

## Séries retenues (74 valeurs)
Croissance du PIB réel (2000-2008), PIB nominal (2000-2008), inflation IPC
moyenne (2005-2008, 2011), IPC général décembre (2009-2010), recettes et dons,
dépenses totales, solde base ordonnancement (2005-2008, 2010-2011 ; 2012 partiel
à fin septembre), dette extérieure (2001-2008), dette / PIB (2006-2008),
exportations / importations / investissement en % du PIB (2005-2010, dont
2008-2010 en prévision du ministère).

## Grandes tendances
- Croissance : 0,4 % (2000) → 3,2 % (2005) → 5,8 % (2008), rupture en 2006.
- Inflation : pic à 6,0 % en moyenne en 2008, retour à 2,7 % en 2011.
- Finances publiques : excédent unique en 2008 (+2,2 Mds FD, dons +205 %),
  déficits en 2006-2007 puis 2010-2011.
- Dette : +112 % entre 2001 et 2008 (47,6 → 100,9 Mds FD), 57,8 % du PIB en
  2008, proche du seuil de 60 % cité par le BIE.
- Investissement brut : 23,2 % du PIB en 2005 → 42,1 % en 2007, porté par les IDE.

## Prévisions (partie séparée, modèle MizanBI)
Méthode : tendance linéaire par moindres carrés ordinaires, intervalle
±1,96 × écart-type résiduel. Horizon 2009-2012.
- Croissance du PIB réel : 6,37 % (2009) → 8,16 % (2012), intervalle ±0,94 pt.
  La tendance dépasse les prévisions du ministère (5,1 à 6,3 %) : borne haute
  naïve, qui ignore la crise de 2009.
- Dette extérieure : 98,8 → 117,6 Mds FD, intervalle ±12,0 Mds FD.
- PIB nominal : 167,9 → 194,1 Mds FD, intervalle ±15,7 Mds FD. Les prévisions
  du ministère (193,6 à 260,6 Mds FD) sont au-dessus de l'intervalle dès 2010 :
  le PIB nominal n'est pas linéaire.
- Pas de prévision : inflation (5 points, trou 2009-2010), recettes et dépenses
  (trou 2009, choc des dons 2008), exportations/importations (2008-2010 déjà des
  prévisions du ministère).

## Limites
- 2001-2004 : contenu non récupérable (cadres, fichiers vides).
- 2009 : pas de total annuel (note T4 absente) ; 2012 : cumuls à fin septembre
  seulement.
- Les bulletins révisent leurs propres chiffres d'une édition à l'autre.
- Le trafic portuaire n'a pas donné de série annuelle comparable (seuls des
  points isolés, ex. importations +74 % en 2008) : mention qualitative seulement.
- Les erreurs résiduelles des prévisions sont des approximations, pas une
  certification.

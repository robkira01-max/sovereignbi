# Benchmark MizanBI — équivalents dans le monde (novembre 2026)

> Complète la section 1 de `PLAN.md`. Date de l'analyse : 2026-11-15. Les prix viennent surtout de blogs et de consultants, pas des pages officielles : à vérifier avant tout usage commercial (voir « Réserves »).

## 1. Cinq familles d'équivalents

| Famille | Exemples | Ce qu'elle fait |
|---|---|---|
| BI classique cloud | Power BI, Tableau, Qlik, Looker | Visualisation et modélisation à grande échelle, IA ajoutée |
| BI open source | Metabase, Superset, Redash | Tableaux de bord auto-hébergés ; Metabase ajoute de l'IA |
| BI conversationnelle | ThoughtSpot, Wren AI, Vanna, Hex, Julius | Questions en langage naturel, couche sémantique |
| Diffusion statistique officielle | .Stat Suite (OCDE, MIT), PxWeb, DHIS2 (santé), Redatam | Publier des données d'instituts de statistique |
| SIG | ArcGIS Online, QGIS, CARTO, Kepler.gl, Felt | Cartes et analyse spatiale |

MizanBI est un hybride : BI conversationnelle + tableaux de bord + SIG, auto-hébergé, en français. Aucun concurrent identifié ne couvre ces quatre points ensemble.

## 2. MizanBI contre Power BI

| Aspect | Power BI | MizanBI | Avantage |
|---|---|---|---|
| Déploiement | Cloud ; Report Server sur site existe | Auto-hébergé, hors ligne, une installation | MizanBI |
| Souveraineté des données | Données dans le cloud Microsoft | Locales ; IA locale (Ollama) ou externe en option | MizanBI |
| Prix | Pro ≈ 14 $/utilisateur/mois ; Premium par utilisateur ≈ 24 $ ; Copilot exige une capacité Fabric (F64 ≈ 5 000 à 8 400 $/mois selon la formule, seuil contesté) | Licence par installation, sans coût par utilisateur | MizanBI à grande échelle ; Power BI pour quelques utilisateurs |
| IA conversationnelle | Copilot, cloud, dépend du modèle sémantique | Texte vers SQL, couche sémantique, SQL visible, refus si pas de source | MizanBI (souveraineté) ; Copilot plus mûr |
| Modélisation | DAX, relations, mesures, Power Query | Couche sémantique YAML, DuckDB | **Power BI, très nettement** |
| Visualisation | Des centaines de visuels, écosystème tiers | Quelques types (cartes, thermique, grille, flux) | **Power BI** |
| Cartographie | Cartes basiques, ArcGIS en extension | Catalogue géo, analyses spatiales, GeoAI, découpage officiel de Djibouti | **MizanBI** |
| Sources de données | Plus de 100 connecteurs | Fichiers, PostgreSQL, MySQL, SQL Server, Comtrade, PDF | **Power BI** |
| Actualisation | Planifiée, passerelles | Synchronisation basique | **Power BI** |
| Sécurité | SSO Entra, sécurité par ligne, étiquettes de sensibilité | Rôles, sessions hachées, SQL en lecture seule, audit | Power BI (échelle entreprise) |
| Conformité | Certifications Microsoft | Loi 25 : consentement, demandes d'accès, pages légales | Dépend du client ; aucune certification pour MizanBI |
| Collaboration | Espaces de travail, abonnements, commentaires | Liens de partage, annotations, favoris, étiquettes | Power BI |
| Exports | PDF, PowerPoint, Excel | Bulletin HTML, PPTX, CSV | Égalité sur l'essentiel |
| Mobile et hors ligne | Application native | Web adaptatif, PWA | Power BI |
| Langues | Interface française, IA surtout en anglais | Français d'abord, anglais | MizanBI pour le français |
| Maturité | 10 ans, énorme communauté | Un développeur, pilote pas encore en production | **Power BI** |

## 3. Ce qui compte

- **Là où MizanBI gagne** : données qui ne peuvent pas quitter le pays ou le serveur (instituts de statistique, banques, administrations), budget incompatible avec Fabric, carte officielle locale, IA hors ligne.
- **Là où il perd** : modélisation (pas d'équivalent de DAX), nombre de visuels, connecteurs, actualisation planifiée, certifications. Ne pas chercher à rattraper Power BI sur ces points.
- **Corrections au benchmark de `PLAN.md`** : Wren AI a retiré son interface de chat (juin 2026) ; son offre ouverte est une couche sémantique en ligne de commande, l'application complète est payante. Metabase a livré l'IA dans sa version ouverte (Metabase 60, avril 2026) avec une clé de modèle fournie par l'utilisateur ; ses pages produit se contredisent sur l'hébergement local.

## 4. S'en inspirer (priorisé)

**De Power BI**
1. Bibliothèque de mesures réutilisables, définies une fois dans la couche sémantique (l'idée de DAX, sans le langage).
2. Synonymes pour les questions : « chômage », « sans-emploi » et « taux de chômage » renvoient à la même mesure.
3. Sécurité par ligne : un utilisateur ne voit que sa région (à vérifier d'abord dans le code, existence non confirmée).
4. Jeux de données certifiés : pastille « validé par l'INSTAD » (rejoint le « certificat de précision »).
5. Abonnements par courriel : bulletin envoyé chaque lundi.
6. Signets et exploration (clic sur une barre pour voir le détail).

**De Metabase et Superset**
7. Questions réutilisables : une question validée devient un objet que d'autres peuvent rouvrir.
8. Éditeur SQL pour les analystes, à côté du chat.
9. Intégration dans un autre site (embedding).

**De Wren AI et des couches sémantiques**
10. Définitions sémantiques dans Git, relues comme du code (les tableaux de bord YAML le permettent déjà).

**De ThoughtSpot et Tableau Pulse**
11. Résumés automatiques : « les chiffres du jour » sans poser de question.

**Des outils de statistique officielle (.Stat Suite, PxWeb)**
12. SDMX (standard d'échange des instituts de statistique) en import et export, plus des métadonnées sur chaque indicateur (source, périodicité, définition). Le plus important si le premier client est un institut de statistique.
13. Page publique de diffusion avec les indicateurs et leur API, séparée de l'espace d'analyse.

**De DHIS2**
14. Hors ligne d'abord et hiérarchie des organisations (pays, région, district), utiles pour la collecte avec une connexion instable.

**Des outils SIG**
15. Animation dans le temps (Kepler.gl) et cartes narratives (ArcGIS StoryMaps) pour les bulletins.
16. Rapports prêts à imprimer, PDF à mise en page fixe, pour les publications officielles.

**Ordre recommandé** : (1) mesures réutilisables et synonymes (plus de valeur pour la précision de l'IA : +17 à +23 points mesurés avec une couche sémantique, voir `PLAN.md` §1.2) ; (2) métadonnées d'indicateurs et SDMX ; (3) abonnements par courriel et résumés automatiques ; (4) sécurité par ligne et jeux de données certifiés.

**À éviter** : un éditeur de visuels à la Power BI ou un langage de formules propre (chantier de dix ans, pas un avantage de MizanBI).

## 5. Réserves

- Les prix viennent de blogs et de consultants. Les sources se contredisent sur le seuil de Copilot (F64 ou capacité plus petite) et sur l'inclusion dans Premium par utilisateur. Vérifier chez Microsoft avant d'écrire un prix dans un document commercial.
- Non trouvé : si Power BI Report Server (sur site) offre Copilot. Ne pas écrire « Power BI ne fonctionne jamais hors ligne » dans le marketing.
- Rien de vérifié sur PxWeb et Redatam ; les remarques s'appuient surtout sur .Stat Suite et DHIS2.
- Pas de prix publics pour ArcGIS Online, CARTO et Felt (sur devis).
- Les avantages et limites de MizanBI sont évalués d'après le code et les échanges, sans test comparatif.

## Sources
- [Power BI Pricing 2026 (EPC Group)](https://www.epcgroup.net/blog/power-bi-pricing-pro-vs-premium-2026)
- [Power BI Pricing: The Copilot Costs Nobody Mentions (Querio)](https://querio.ai/articles/power-bi-pricing-copilot-costs-nobody-mentions)
- [Power BI Pro vs PPU vs Fabric 2026 (o365hq)](https://o365hq.com/blog/power-bi-pro-vs-premium-per-user-vs-fabric-capacity-licensing-2026)
- [Power BI in 2026 (AlphaBold)](https://www.alphabold.com/power-bi-2026-updates/)
- [Wren AI, déploiement sur site](https://www.getwren.ai/en/on-premise)
- [Wren Journal, juin 2026](https://www.getwren.ai/post/genbi-for-ai-agents-open-context-layer)
- [Metabase, IA et version ouverte](https://www.metabase.com/articles/ai-answers-open-source-metabase)
- [Metabase 60, notes de version](https://www.metabase.com/releases-ai/metabase-60)
- [.Stat Suite (SDMX)](https://sdmx.org/?p=10575)
- [Comparatif ArcGIS Online, Felt, CARTO](https://www.spotsaas.com/compare/arcgis-online-vs-carto)
- [QGIS contre ArcGIS 2026 (Atlas)](https://atlas.co/blog/qgis-vs-arc-gis-complete-comparison-for-2026/)

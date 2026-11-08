# Propositions P-022 à P-026 — changements benchmark (7 novembre 2026)

Approuvées par Robleh le 7 novembre 2026, à partir du benchmark des tendances
actuelles (BI agentique, couche sémantique, souveraineté hors ligne, SIG
vectoriel / PMTiles, concurrents contingentés). Appliquées dans cette app React.

## P-022 — Agent BI multi-étapes (`src/pages/Chat.tsx`)

Après chaque réponse démo, l'agent propose 3 suites logiques cliquables
(comparer avec 2024, voir par région, voir l'évolution) et affiche une
2e vérification : le taux pondéré est recalculé depuis les régions et comparé
au KPI (23,5 %, emploi_region, 2024 — coïncide en démo, sinon « écart détecté »).
Une alerte démo est affichée en haut du chat : Obock 29,1 %, seuil 25 % dépassé.
SQL toujours visible. Aucun taux de précision affirmé (pas de 95 %).

## P-023 — Preuve de confiance partout (`src/components/Proof.tsx`, `src/pages/Certificate.tsx`)

Provenance (table + année démo), SQL et score de confiance affichés sous
chaque tuile de dashboard et chaque réponse du chat (mode Données).
État « Je m'abstiens » quand la question est hors périmètre démo
(emploi, population, pauvreté, Djibouti, 2024) : l'agent refuse d'inventer.
Page « Certificat de précision » (lien depuis l'Accueil et la sidebar) :
méthode en 5 points — couche sémantique, SQL visible, dry-run, abstention,
provenance — et ce qu'elle ne promet pas (aucun score global affirmé,
prévisions 2030 indicatives, quartiers approximatifs, flux illustratifs masqués).

## P-024 — Digests proactifs (`src/pages/Bulletins.tsx`)

Section « Bulletins » (Accueil, Dashboards, sidebar). Bulletin narratif
hebdomadaire démo, semaine du 3 novembre 2026, en 3 points, avec graphique
et tableau par région, ouvrable offline. Planification affichée : chaque
lundi, sans envoi réel en mode démo. Export : HTML auto-suffisant généré
côté client (téléchargement, pas d'appel API).

## P-025 — Offline terrain + MizanSIG unifié (`src/pages/Sig.tsx`)

Le SIG est un seul module « MizanSIG » : ADM1 / ADM2 / quartiers,
bivariée pauvreté × chômage, flux. Badge « Hors ligne » visible :
données embarquées, aucune requête réseau en mode démo, polices système
uniquement. Note PWA / collecte terrain à venir.
CDN externes retirés : le seul trouvé était Google Fonts
(`fonts.googleapis.com`, dans `index.html` et `src/index.css`) — supprimé
et remplacé par les piles système. Aucune tuile Leaflet / OpenStreetMap
en ligne, aucun autre CDN (grep vérifié : pas de unpkg, pas de tile.openstreetmap).
Flux commerciaux : choix retenu — masqués par défaut derrière un interrupteur
« Afficher les flux illustratifs » (désactivé par défaut), avec un panneau
« Données Comtrade réelles à brancher (clé backend uniquement, non incluse) ».

## P-026 — Gel et modèle commercial (README, Accueil)

Encadré « Gel pilote » sur l'Accueil : aucune nouvelle fonctionnalité avant
le pilote INSTAD, sauf P-022 et P-023. Modèle affiché : « Licence annuelle
par installation, sans quota de questions, sans cloud obligatoire ».
Aucun compteur de requêtes, aucun paywall, aucun prix par siège,
aucun multi-tenant cloud ajouté.

## Suppressions / corrections

- Flux fictifs retirés des démos institutionnelles (voir P-025).
- Aucune mention du règlement européen restante : conformité Loi 25 / LPRPDE partout.
- Six régions partout, jamais cinq.
- Chiffres incohérents : 26,8 % national et 1 062 000 ne sont repris nulle part
  comme chiffres nationaux ; le 26,8 % ne survit que comme valeur du quartier
  Balbala, déjà documentée, et dans l'écart prototype documenté (README, demo.ts).
- Mode « Général » du chat : séparé du mode « Données », avec avertissement
  clair qu'il ne s'appuie pas sur les données et peut halluciner.

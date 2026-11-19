# Prompts Claude Code : P-086a (serveur) puis P-086b (client)

À lancer dans cet ordre, dans deux sessions séparées. P-086b dépend de P-086a et de P-083. Ne pas les fusionner en une seule session : la première touche des chemins de fichiers, des droits et des identifiants (relecture de sécurité obligatoire) ; la seconde est de l'interface, avec un autre risque.

## Prompt 1 : P-086a, serveur et connecteurs de niveau A

````text
/model opus

Tâche : P-086a (serveur de l'espace de travail et connecteurs de niveau A). Lis d'abord CLAUDE.md et la section P-086 de docs/proposals_pack-audit_P073-P086.md (si le fichier n'est pas dans docs/, dis-le-moi). Cette tâche touche des chemins de fichiers, les droits et les identifiants : changement sensible.

Avant de coder
1. Vérifie que P-083 (clés par personne) est livré. Sinon, arrête-toi et dis-le-moi : P-086a en dépend pour le journal (qui a connecté quoi).
2. Montre-moi un plan court (fichiers touchés, tables, endpoints, tests) et attends mon accord. Rien hors de ce plan sans accord.
3. Deux choix à me faire valider dans le plan :
   - le format du stockage des copies figées (répertoire, nommage, versions) ;
   - la façon de refuser les chemins dangereux (`..`, liens symboliques, chemins absolus, noms avec octet nul).

Périmètre (P-086a seulement)
- `app/workspace/` : interface `Connector` (lister, lire en flux, empreinte) avec deux implémentations : dossier monté côté serveur (volume en lecture seule) et SMB/SFTP si une bibliothèque sous licence MIT/Apache/BSD existe (sinon, dossier monté seulement, et dis-le-moi).
- Tables `workspace_sources` (type, nom, racine autorisée, mode, enabled_by, état) et `workspace_files` (chemin relatif, taille, SHA-256, version, statut, source). Préfixe de tables cohérent avec D-3.
- Import en copie figée : lecture en flux, SHA-256, nouvelle version si le fichier source change (l'ancienne reste), statuts Importé / Indexé / Anomalies / Certifié / Périmé.
- Indexation CSV, XLSX, SDMX, PDF texte. Pas d'OCR, pas de PyMuPDF (AGPL).
- `WORKSPACE_ALLOW_THIRD_PARTY=false` par défaut : les types Google Drive, SharePoint et OneDrive n'existent pas côté API (erreur explicite), pas seulement masqués côté client.
- Endpoints sous RequireRole : lecture = viewer, import = editor, création et activation de connecteurs = admin.
- Toute lecture de lignes passe par `DataStore.execute` (sécurité par ligne, P-068). Les droits d'un fichier sont ceux de son dossier.
- Entrées dans le journal d'audit chaîné pour chaque connexion, import et refus.
- Identifiants de connecteurs : chiffrés au repos, jamais renvoyés par l'API ni écrits dans les journaux.
- Le contenu d'un fichier n'est jamais envoyé à un modèle externe.

Hors périmètre (ne pas faire)
Client (mizanbi-client), niveau B (clouds tiers), agent de bureau, écriture dans la source, OCR, synchronisation temps réel.

Critères d'acceptation, chacun avec un test
- Admin connecte un dossier ; viewer voit les fichiers mais ne peut pas importer ; editor importe.
- Chemin hors racine (`../`, lien symbolique, absolu) refusé et journalisé.
- Un import enregistre un SHA-256 ; modifier la source crée une version sans écraser l'ancienne.
- Avec `WORKSPACE_ALLOW_THIRD_PARTY=false`, créer un connecteur Google Drive ou SharePoint renvoie une erreur, et `tests/test_network_isolation.py` passe.
- Un utilisateur sans droit sur un dossier ne voit ni ses fichiers ni leurs noms.
- Aucun identifiant de connecteur dans les réponses API ni dans les journaux (test qui le vérifie).
- Faux fournisseur LLM qui fait échouer le test s'il reçoit du contenu de fichier.

Fin de tâche
- Lance toute la suite pytest et donne-moi le nombre de tests avant et après.
- Lance le sous-agent security-reviewer sur `app/workspace/` et sur les changements d'authentification ; donne-moi ses constats par gravité.
- Mets à jour docs/proposals.md (statut de P-086a) et THIRD_PARTY.md si une dépendance est ajoutée.
- Termine par un résumé : ce qui est fait, ce qui n'est pas vérifié, les fichiers non suivis laissés de côté, et ce qui reste avant P-084.
- Ne commite pas sans mon accord.
````

## Prompt 2 : P-086b, espace de travail, colonne de droite et bulle flottante (mizanbi-client)

````text
Tâche : P-086b (interface : espace de travail, colonne de droite commune, assistant en bulle flottante) dans mizanbi-client. Lis d'abord CLAUDE.md, la section P-086 de docs/proposals_pack-audit_P073-P086.md et les maquettes docs/maquettes/05-assistant-bulle.png, 06-espace-de-travail.png et 09-ajout-connecteur.png. Les maquettes montrent la disposition ; l'identité visuelle, les composants et les chaînes de caractères existants du client priment.

Avant de coder
1. Vérifie que P-086a est livré (endpoints de l'espace de travail). Liste ceux que tu utiliseras. Si un endpoint manque, arrête-toi et dis-le-moi : n'invente pas d'API et ne modifie pas le serveur.
2. Montre-moi un plan court (routes, composants, état partagé, tests) et attends mon accord.

Périmètre (P-086b seulement)
- Espace de travail (route principale) : dossiers, liste de fichiers, statuts (Importé, Indexé, Anomalies, Certifié, Périmé) en pastille avec texte, glisser-déposer pour l'import (réservé aux editors), indicateur de stockage, état vide, état d'erreur, chargement.
- Colonne de droite commune à tous les écrans : `ConnectorsPanel` (liste des connecteurs et leur état, bouton Ajouter) et `ActiveContext` (documents connectés, projet actif, objectif actuel). Elle lit l'état réel depuis l'API.
- Ajout d'un connecteur en 3 étapes (type, dossiers, autorisations). Seuls les types disponibles côté API sont actifs. Les clouds tiers (Google Drive, SharePoint, OneDrive) apparaissent désactivés avec l'explication, sans aucun bouton de connexion tant que le serveur ne les expose pas.
- `AssistantBubble` : bulle flottante en bas à droite de tous les écrans, montée une fois à la racine de l'application.
  - fermée : bouton « Assistant MizanBI » ; ouverte : panneau de chat non modal qui se superpose ;
  - la conversation et l'état ouvert ou fermé persistent quand on change de route (état partagé à la racine, pas par page) ;
  - elle lit le contexte de l'écran (fichier ou tableau de bord affiché, projet actif) via un fournisseur de contexte, et l'affiche dans son en-tête avec le mode strict ;
  - elle réutilise le chat existant (P-080) : plan d'action, pastille « Calculé » (formule, version, run) ou « Exploratoire, non certifié » selon la réponse du serveur. Le client n'invente jamais une pastille « Calculé » ;
  - accessibilité : ouverture et fermeture au clavier, focus visible, Échap ferme, `aria-live` poli pour les nouvelles réponses, nom accessible sur le bouton ; sur mobile, le panneau occupe tout l'écran.
- Navigation latérale : Espace de travail, Tableaux de bord, Cartes, Jeux de données, Pack Audit, Partages, Administration. L'ancienne route « Missions » redirige vers l'espace de travail avec la bulle ouverte ; l'historique des conversations passe dans le panneau.
- Français et anglais comme le reste du client.

Hors périmètre (ne pas faire)
Changements serveur, connecteurs de niveau B, agent de bureau, refonte visuelle des autres volets (Tableaux, Cartes, Jeux, Audit, Partages, Administration : ils reçoivent seulement la nouvelle navigation, la colonne de droite et la bulle), OCR.

Critères d'acceptation, chacun avec un test (utilise le framework de test déjà en place)
- Un viewer voit les fichiers mais n'a pas de zone d'import ; un editor peut importer.
- La bulle est présente sur chaque route, garde sa conversation et son état quand on change d'écran.
- Échap ferme la bulle ; le focus revient au bouton ; la nouvelle réponse est annoncée.
- Aucune pastille « Calculé » sans formule, version et run fournis par le serveur.
- Les clouds tiers sont désactivés dans l'interface quand le serveur ne les expose pas.
- Aucun identifiant ni jeton n'est stocké dans le navigateur ni écrit dans la console.
- Les états vide, chargement et erreur existent pour l'espace de travail et la colonne de droite.

Fin de tâche
- Lance les tests du client, le contrôle de types et le lint ; donne les nombres avant et après.
- Ouvre l'application dans un navigateur et vérifie le parcours : connexion, espace de travail, ajout d'un connecteur, ouverture de la bulle, changement d'écran, fermeture. Dis ce que tu as réellement vérifié et ce que tu n'as pas pu vérifier.
- Mets à jour docs/proposals.md (statut de P-086b).
- Termine par un résumé : ce qui est fait, ce qui n'est pas vérifié, les fichiers non suivis laissés de côté.
- Ne commite pas sans mon accord.
````

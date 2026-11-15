# Contrat de traitement des données (DPA) — MizanBI

> **BROUILLON TECHNIQUE — non validé par un juriste.** Les passages `[À COMPLÉTER : …]` dépendent de décisions de l'éditeur (entité, hébergeur, fournisseur d'IA). Les faits techniques (sections 4, 5 et annexes) décrivent le code au 2026-11-15 ; les vérifier avant signature. Ne pas signer en l'état.

## 1. Parties et rôles
- **Client** (banque, ONG, administration, institut de statistique) : **responsable du traitement** des données qu'il importe dans MizanBI (fichiers, tables, tableaux de bord, commentaires).
- **Éditeur** : `[À COMPLÉTER : entité juridique, adresse, contact]` — **sous-traitant** pour ces données ; **responsable du traitement** seulement pour les données de compte et de journalisation nécessaires à faire fonctionner le service (e-mail, rôle, sessions, consentements, journal d'audit).
- Droit applicable et juridiction : `[À COMPLÉTER]`. Cadres visés : Loi 25 (Québec), LPRPDE/PIPEDA (Canada), et le droit djiboutien applicable `[À COMPLÉTER : à confirmer par un juriste local]`.

## 2. Objet, durée, nature du traitement
Fourniture d'une plateforme d'analyse (questions en langage naturel, tableaux de bord, cartes, exports, bulletins par courriel). Durée : celle du contrat. Catégories de données : celles que le client importe (il les déclare) ; personnes concernées : celles du client. L'éditeur ne choisit ni ne consulte le contenu importé.

## 3. Obligations de l'éditeur
1. Traiter les données **uniquement sur instruction documentée** du client (le contrat et l'usage normal de la plateforme).
2. Confidentialité : accès restreint aux personnes autorisées, tenues à la confidentialité `[À COMPLÉTER : engagements du personnel]`.
3. Aider le client à répondre aux demandes des personnes concernées (accès, rectification, suppression) — voir section 7.
4. Notifier le client d'un incident touchant ses données — voir section 8.
5. Restituer ou supprimer les données à la fin du contrat — voir section 7.
6. Fournir les informations nécessaires pour démontrer la conformité et permettre un audit raisonnable `[À COMPLÉTER : modalités, préavis, coût]`.

## 4. Mesures de sécurité (état du code)
- **Contrôle d'accès** : rôles viewer/editor/admin ; sessions à jeton aléatoire dont seul le hachage SHA-256 est stocké ; verrouillage après échecs ; mots de passe bcrypt ; garde « dernier administrateur » ; pas d'authentification à deux facteurs (à signaler au client).
- **Requêtes** : SQL généré en lecture seule, liste blanche de tables, une instruction, limite de lignes (`sql_guard`).
- **Journal d'audit** chaîné (SHA-256) des actions d'administration ; ne contient ni mots de passe ni e-mails. **Limite : aucun outil intégré ne vérifie encore l'intégrité de la chaîne** (à contrôler par script).
- **Réseau** : l'API n'émet pas d'appels sortants autres que ceux décrits en annexe B ; en-têtes de sécurité ; limitation de débit.
- **Secrets** hors du code (variables d'environnement). Courriels : STARTTLS obligatoire.
- **Limites à déclarer honnêtement** : pas de certification de sécurité (ISO 27001, SOC 2) ; les mots de passe de connexion aux sources externes sont chiffrés (Fernet), mais pas de chiffrement applicatif des données importées au repos (dépend du chiffrement du disque de l'hébergeur `[À COMPLÉTER]`) ; **pas de sécurité par ligne** (tout utilisateur autorisé sur une table voit toutes ses lignes) ; test d'intrusion par un tiers non réalisé.
- Sauvegardes : objectifs RTO / RPO `[À COMPLÉTER : valeurs réellement testées — le code documente RPO < 24 h ; aucune restauration n'est testée automatiquement]`.

## 5. Sous-traitants ultérieurs et transferts
Liste en annexe A ; le fournisseur d'IA fait l'objet de l'**annexe D**. Le client est informé de tout changement `[À COMPLÉTER : préavis]` et peut s'y opposer. Aucun transfert hors du lieu d'hébergement choisi, **sauf** si le client active un fournisseur d'IA externe (annexe B) : dans ce cas, le texte des questions et des extraits de données utiles à la réponse quitte l'hébergement. Mode « IA locale » : aucun transfert. Mode « strict » (`SOVEREIGN_AI_STRICT`, **actif par défaut dès qu'un fournisseur externe est configuré**) : seuls la question, les noms de tables et de colonnes et le modèle sémantique sont transmis — aucune ligne de données, aucun résultat, aucun extrait de document. Si le mode strict est désactivé explicitement (`SOVEREIGN_AI_STRICT=0`), des lignes d'exemple, des résultats et des extraits peuvent être transmis. `[À COMPLÉTER : confirmer que le mode strict reste actif pour ce client, ou la décision écrite de le désactiver]`

## 6. Localisation des données
Hébergement : `[À COMPLÉTER : fournisseur, région]` (décision en suspens du propriétaire).

## 7. Droits des personnes, restitution et suppression
- Outils fournis (administrateur) : `GET /compliance/account/{id}/export` (export JSON d'un compte), `DELETE /compliance/account/{id}?confirm=<e-mail>` (suppression : compte, sessions, consentements, abonnements ; demandes d'accès pseudonymisées).
- **Conservé** : journal d'audit (identifiant numérique seulement, intégrité de la chaîne) ; sauvegardes jusqu'à expiration de la rétention `[À COMPLÉTER]`.
- Fin de contrat : restitution des exports du client (tableaux, fichiers SDMX-CSV/CSV) puis suppression des jeux de données importés sous `[À COMPLÉTER : délai]` jours. **Aucun outil automatique de purge des données importées n'existe aujourd'hui** : procédure manuelle de l'administrateur.

## 8. Incidents
Notification au client **sans délai injustifié et au plus tard 72 h** après la prise de connaissance d'un incident touchant ses données `[À COMPLÉTER : confirmer le délai avec le client et le droit applicable]`, avec : nature, données et volumes estimés, conséquences probables, mesures prises. Procédure interne : `docs/incident-procedure.md` ; registre : `POST /compliance/incidents`, `GET /compliance/incidents`, `PUT /compliance/incidents/{id}`.

## 9. Responsabilité, résiliation
`[À COMPLÉTER PAR UN JURISTE]`.

---
### Annexe A — Sous-traitants ultérieurs
| Rôle | Fournisseur | Données | Lieu |
|---|---|---|---|
| Hébergement | `[À COMPLÉTER]` | toutes | `[À COMPLÉTER]` |
| Courriel (bulletins, si activé) | `[À COMPLÉTER : serveur SMTP]` | adresses, bulletins | `[À COMPLÉTER]` |
| IA (si externe) | voir **Annexe D** (ou aucun : modèle local) | selon le mode (Annexe D.2) | voir Annexe D.1 |

### Annexe B — Flux sortants du code
Fournisseur d'IA configuré par `LLM_PROVIDER` (contenu transmis selon `SOVEREIGN_AI_STRICT`, voir §5) ; SMTP si `SMTP_HOST` défini ; sources publiques optionnelles (Comtrade, StatCan…) lorsque le client les active : aucune donnée du client n'y est envoyée. `tests/test_network_isolation.py` liste les URL de base autorisées.

### Annexe C — Données traitées par l'éditeur comme responsable
Compte (e-mail, rôle, dates), sessions (hachées), consentements (aucune IP conservée), demandes d'accès, abonnements courriel, journal d'audit. Rétention : `[À COMPLÉTER]`.

---
### Annexe D — Fournisseur d'IA (sous-traitant ultérieur)

> **À remplir pour chaque client avant la mise en service d'un LLM externe.** Si le client choisit le modèle local (configuration A), seule la case D.1 est à cocher : aucune donnée ne quitte l'hébergement. Les éléments marqués `[À COMPLÉTER]` viennent du **contrat du fournisseur** et de ses réponses écrites ; l'éditeur ne les affirme pas à sa place. Brouillon technique non validé par un juriste.

#### D.1 Configuration retenue et identification
| Élément | Valeur |
|---|---|
| Configuration (cocher une) | ☐ **A — modèle local** (`LLM_PROVIDER=ollama`) · ☐ **B — externe, mode strict** · ☐ **C — externe, mode strict désactivé** (décision écrite du client requise, voir D.5) |
| Fournisseur (entité juridique, adresse) | `[À COMPLÉTER]` |
| Pays et région de traitement des requêtes | `[À COMPLÉTER]` |
| Juridiction applicable au fournisseur (lois d'accès des autorités à ses données) | `[À COMPLÉTER : à faire confirmer par un juriste]` |
| Modèle utilisé (`KIMI_MODEL`) et version | `[À COMPLÉTER]` |
| Point d'accès (`KIMI_BASE_URL`, domaine seulement) | `[À COMPLÉTER]` |
| Date d'entrée en vigueur · contact du fournisseur pour la protection des données | `[À COMPLÉTER]` |

*Note technique : l'emplacement externe de la configuration s'appelle `kimi` dans le code (`LLM_PROVIDER=kimi`), mais il accepte **tout fournisseur offrant une API compatible « chat/completions »** : l'adresse n'est jamais codée en dur, elle vient de `KIMI_BASE_URL`. Le nom `kimi` n'implique donc pas que ce fournisseur soit utilisé.*

#### D.2 Données transmises au fournisseur, selon la configuration
| Fonction | A — local | B — externe, strict | C — externe, non strict |
|---|---|---|---|
| Question de l'utilisateur | reste local | **transmise** | **transmise** |
| Noms de tables et de colonnes, types | reste local | **transmis** | **transmis** |
| Modèle sémantique (mesures, filtres, synonymes écrits par l'administrateur) | reste local | **transmis** | **transmis** |
| Questions et SQL des exemples d'apprentissage | reste local | **transmis** | **transmis** |
| Historique du chat | reste local | questions de l'utilisateur seulement | questions **et réponses précédentes** |
| Catalogue de couches géographiques (géo-IA) | reste local | **transmis** | **transmis** |
| 3 lignes d'exemple par table | reste local | **jamais** | **transmises** |
| Lignes de résultat (jusqu'à 50) pour rédiger la réponse | reste local | **jamais** (réponse rédigée localement) | **transmises** |
| Extraits de documents importés | reste local | **jamais** | **transmis** |
| Lignes de chaque tuile (« insights » IA, demandés automatiquement à l'ouverture d'un tableau de bord) | reste local | **jamais** (fonction désactivée) | **transmises** |
| Valeurs citées dans les messages d'erreur de la base | reste local | masquées | **transmises** |

Remarques : (1) les noms de tables et de colonnes et les questions peuvent eux-mêmes être sensibles : le mode strict **réduit** la fuite, il ne la supprime pas. (2) La sécurité par ligne filtre les lignes d'exemple et de résultat d'un compte non administrateur ; **un compte administrateur voit tout, y compris dans les lignes transmises en configuration C**. (3) En cas de panne du fournisseur, un disjoncteur (3 échecs consécutifs, 5 minutes) **bascule les requêtes vers le modèle local** (`OLLAMA_URL`) : pendant ce temps, le contenu reste local ; l'adresse `OLLAMA_URL` doit donc désigner un serveur sous le contrôle de l'opérateur.

#### D.3 Engagements à obtenir du fournisseur (par écrit) 
| Point | Réponse du fournisseur | Preuve (document, date) |
|---|---|---|
| Les données envoyées **ne servent pas à entraîner** ses modèles | `[À COMPLÉTER]` | `[À COMPLÉTER]` |
| **Durée de conservation** des requêtes et réponses ; option de conservation nulle | `[À COMPLÉTER]` | `[À COMPLÉTER]` |
| **Lieu** de traitement et de stockage ; transferts internationaux | `[À COMPLÉTER]` | `[À COMPLÉTER]` |
| **Sous-traitants** du fournisseur (liste, lieux) et préavis de changement | `[À COMPLÉTER]` | `[À COMPLÉTER]` |
| **Demandes d'accès d'autorités** : politique, notification au client, loi applicable | `[À COMPLÉTER]` | `[À COMPLÉTER]` |
| **Notification d'incident** : délai garanti (doit permettre au client de respecter les 72 h du §8) | `[À COMPLÉTER]` | `[À COMPLÉTER]` |
| **Certifications / audits** de sécurité disponibles | `[À COMPLÉTER]` | `[À COMPLÉTER]` |
| **Suppression** des données à la fin du contrat ; accès à un journal des requêtes | `[À COMPLÉTER]` | `[À COMPLÉTER]` |
| Accès du personnel du fournisseur au contenu des requêtes (modération, support) | `[À COMPLÉTER]` | `[À COMPLÉTER]` |

*Tant qu'une ligne essentielle (entraînement, conservation, lieu, accès des autorités, incident) reste sans réponse écrite, la configuration B ou C ne devrait pas être mise en service.*

#### D.4 Mesures techniques côté éditeur (état du code)
- Connexion **HTTPS obligatoire** vers le fournisseur (une adresse en `http://` est refusée) ; clé d'API en variable d'environnement, jamais dans le dépôt.
- **Mode strict automatique** dès qu'un fournisseur externe est configuré (`SOVEREIGN_AI_STRICT` vide) ; le désactiver émet un avertissement au démarrage.
- **Plafond de dépense quotidien** (`KIMI_DAILY_BUDGET_USD`) et **délai maximal** par requête (`KIMI_TIMEOUT`) ; la limitation de débit de l'API (par adresse cliente) s'applique aussi aux appels qui déclenchent l'IA, mais il n'existe pas de limite de requêtes propre au fournisseur.
- **Disjoncteur** avec repli sur le modèle local (D.2, remarque 3).
- L'**avis de confidentialité** de l'application (`GET /compliance/notice`) indique le fournisseur, l'emplacement et le mode strict réellement actifs : le client peut le vérifier lui-même.
- Le code n'inscrit pas le contenu des requêtes dans ses journaux applicatifs `[À COMPLÉTER : à confirmer par une revue de code indépendante]`.

#### D.5 Changements
- **Changement de fournisseur** (nouvelle entité ou nouvelle région) = changement de sous-traitant ultérieur : préavis de `[À COMPLÉTER : nombre]` jours, droit d'opposition du client (§5).
- **Changement de version du modèle chez le même fournisseur** : information du client, sans droit d'opposition `[À COMPLÉTER : à confirmer]`.
- **Désactivation du mode strict** (configuration C) : uniquement sur **décision écrite du client**, datée, identifiant la personne qui la prend ; consignée ici : `[À COMPLÉTER : date, nom, fonction]`.
- Toute modification de `LLM_PROVIDER`, `KIMI_BASE_URL`, `KIMI_MODEL` ou `SOVEREIGN_AI_STRICT` sur le serveur du client est tracée par l'opérateur `[À COMPLÉTER : où]` (la configuration n'est pas inscrite au journal d'audit de l'application).

#### D.6 Limites à déclarer honnêtement
- **Aucune garantie technique** sur ce que le fournisseur fait des données reçues : seule la confiance contractuelle et ses preuves (D.3) comptent.
- Le mode strict peut **réduire la précision** des réponses (moins de contexte, réponses rédigées localement) ; l'effet **n'a pas été mesuré**.
- Aucune évaluation de sécurité du fournisseur par un tiers n'a été réalisée par l'éditeur.
- Le modèle local (A) n'envoie rien mais exige un serveur adapté (GPU) ; sur un serveur sans GPU, les petits modèles sont très lents.

#### D.7 Accord du client
Configuration retenue : `[À COMPLÉTER : A / B / C]` · Représentant du client : `[À COMPLÉTER]` · Date : `[À COMPLÉTER]` · Représentant de l'éditeur : `[À COMPLÉTER]`.

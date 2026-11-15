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
- **Journal d'audit** chaîné (SHA-256) des actions d'administration ; ne contient ni mots de passe ni e-mails.
- **Réseau** : l'API n'émet pas d'appels sortants autres que ceux décrits en annexe B ; en-têtes de sécurité ; limitation de débit.
- **Secrets** hors du code (variables d'environnement). Courriels : STARTTLS obligatoire.
- **Limites à déclarer honnêtement** : pas de certification de sécurité (ISO 27001, SOC 2) ; les mots de passe de connexion aux sources externes sont chiffrés (Fernet), mais pas de chiffrement applicatif des données importées au repos (dépend du chiffrement du disque de l'hébergeur `[À COMPLÉTER]`) ; **pas de sécurité par ligne** (tout utilisateur autorisé sur une table voit toutes ses lignes) ; test d'intrusion par un tiers non réalisé.
- Sauvegardes : objectifs RTO / RPO `[À COMPLÉTER : valeurs réellement testées — le code documente RPO < 24 h ; aucune restauration n'est testée automatiquement]`.

## 5. Sous-traitants ultérieurs et transferts
Liste en annexe A. Le client est informé de tout changement `[À COMPLÉTER : préavis]` et peut s'y opposer. Aucun transfert hors du lieu d'hébergement choisi, **sauf** si le client active un fournisseur d'IA externe (annexe B) : dans ce cas, le texte des questions et des extraits de données utiles à la réponse quitte l'hébergement. Mode « IA locale » : aucun transfert. Mode « strict » (`SOVEREIGN_AI_STRICT`, **actif par défaut dès qu'un fournisseur externe est configuré**) : seuls la question, les noms de tables et de colonnes et le modèle sémantique sont transmis — aucune ligne de données, aucun résultat, aucun extrait de document. Si le mode strict est désactivé explicitement (`SOVEREIGN_AI_STRICT=0`), des lignes d'exemple, des résultats et des extraits peuvent être transmis. `[À COMPLÉTER : confirmer que le mode strict reste actif pour ce client, ou la décision écrite de le désactiver]`

## 6. Localisation des données
Hébergement : `[À COMPLÉTER : fournisseur, région]` (décision en suspens du propriétaire).

## 7. Droits des personnes, restitution et suppression
- Outils fournis (administrateur) : `GET /compliance/account/{id}/export` (export JSON d'un compte), `DELETE /compliance/account/{id}?confirm=<e-mail>` (suppression : compte, sessions, consentements, abonnements ; demandes d'accès pseudonymisées).
- **Conservé** : journal d'audit (identifiant numérique seulement, intégrité de la chaîne) ; sauvegardes jusqu'à expiration de la rétention `[À COMPLÉTER]`.
- Fin de contrat : restitution des exports du client (tableaux, fichiers SDMX-CSV/CSV) puis suppression des jeux de données importés sous `[À COMPLÉTER : délai]` jours. **Aucun outil automatique de purge des données importées n'existe aujourd'hui** : procédure manuelle de l'administrateur.

## 8. Incidents
Notification au client **sans délai injustifié et au plus tard 72 h** après la prise de connaissance d'un incident touchant ses données `[À COMPLÉTER : confirmer le délai avec le client et le droit applicable]`, avec : nature, données et volumes estimés, conséquences probables, mesures prises. Procédure interne : `docs/incident-procedure.md` ; registre : `POST/GET/PUT /compliance/incidents`.

## 9. Responsabilité, résiliation
`[À COMPLÉTER PAR UN JURISTE]`.

---
### Annexe A — Sous-traitants ultérieurs
| Rôle | Fournisseur | Données | Lieu |
|---|---|---|---|
| Hébergement | `[À COMPLÉTER]` | toutes | `[À COMPLÉTER]` |
| Courriel (bulletins, si activé) | `[À COMPLÉTER : serveur SMTP]` | adresses, bulletins | `[À COMPLÉTER]` |
| IA (si externe) | `[À COMPLÉTER : Kimi / Groq / autre]` ou aucun (Ollama local) | questions, extraits | `[À COMPLÉTER]` |

### Annexe B — Flux sortants du code
Fournisseur d'IA configuré par `LLM_PROVIDER` (contenu transmis selon `SOVEREIGN_AI_STRICT`, voir §5) ; SMTP si `SMTP_HOST` défini ; sources publiques optionnelles (Comtrade, StatCan…) lorsque le client les active : aucune donnée du client n'y est envoyée. `tests/test_network_isolation.py` liste les URL de base autorisées.

### Annexe C — Données traitées par l'éditeur comme responsable
Compte (e-mail, rôle, dates), sessions (hachées), consentements (aucune IP conservée), demandes d'accès, abonnements courriel, journal d'audit. Rétention : `[À COMPLÉTER]`.

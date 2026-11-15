# Procédure d'incident de sécurité — MizanBI

Outil : registre `POST /compliance/incidents` (admin). **Ne jamais mettre de données personnelles dans les descriptions** (le registre n'est pas chiffré).

## 1. Détecter et qualifier (≤ 1 h)
Sources : alertes du journal d'audit (`GET /audit/verify` en échec), signalements de clients, journaux du serveur, échecs de connexion anormaux. Ouvrir une entrée : gravité (`low|medium|high|critical`), catégorie, `personal_data_involved` (vrai dès qu'un doute existe).

## 2. Contenir
Révoquer clés API (changer `SOVEREIGN_*_KEY`), désactiver les comptes concernés (`PUT /auth/users/{id}`), couper les abonnements courriel (`SOVEREIGN_SUBSCRIPTIONS=0`), isoler le serveur si nécessaire. Noter chaque action : `PUT /compliance/incidents/{id}` avec `action`, statut `contained`.

## 3. Évaluer
Quelles données, quels clients, quelle période ? Utiliser le journal d'audit chaîné (vérifier son intégrité d'abord) et les journaux d'hébergement. Si le journal est altéré, le dire.

## 4. Notifier
- **Clients concernés** : au plus tard 72 h après la prise de connaissance (contenu minimal : voir DPA §8). Enregistrer `clients_notified_at`. `GET /compliance/incidents` signale en `overdue_notifications` les incidents avec données personnelles non notifiés après 72 h.
- **Autorités** (CAI Québec, Commissariat à la protection de la vie privée du Canada, autorité djiboutienne) : c'est **le client, responsable du traitement, qui décide et notifie** ; l'éditeur l'y aide. `[À COMPLÉTER : confirmer avec un juriste pour les cas où l'éditeur est lui-même responsable.]`

## 5. Corriger et clore
Cause racine, correctif, test de non-régression, rotation des secrets, statut `resolved`. Revue écrite sous 30 jours : ce qui a marché, ce qui manque.

## Limites actuelles
Pas d'astreinte ni de supervision automatique ; pas d'exercice de simulation réalisé ; le registre est un fichier local (à sauvegarder avec le reste).

# Relecture humaine — module `app/auth/`

**Date :** 2026-11-09  
**Révisé par :** (nom du propriétaire à signer)  
**Statut :** ⏳ En attente de signature

---

## Ce que fait le module

Le module `app/auth/` gère la connexion par email/mot de passe pour les utilisateurs de l'interface web. Il est **distinct** du système de clés API (`X-Api-Key`) utilisé par les intégrations.

---

## Fichier 1 — `security.py` (cryptographie et base de données)

### Hachage des mots de passe

| Paramètre | Valeur | Commentaire |
|-----------|--------|-------------|
| Algorithme | **bcrypt** | Standard industriel, résistant aux GPU |
| Coût | 12 rounds | ~300 ms par vérification sur un CPU moderne |
| Limite | 72 octets | Limite native de bcrypt — les mots de passe plus longs sont refusés proprement |

> ⚠️ **À noter :** bcrypt est utilisé (pas Argon2id qui est recommandé dans CLAUDE.md pour LexBouti). Bcrypt à 12 rounds est acceptable pour un MVP. Pour une mise en production à fort trafic, envisager la migration vers Argon2id.

### Stockage des sessions

Les tokens de session sont des chaînes aléatoires de 256 bits (32 octets, `secrets.token_urlsafe`). **Seul leur empreinte SHA-256** est stockée en base — un vol de la base de données ne permet pas de rejouer les sessions.

### Protection anti-timing

Un hash fictif (`_DUMMY_HASH`) est vérifié quand l'email n'existe pas, afin que le temps de réponse soit identique qu'un compte existe ou non — évite l'énumération des comptes.

### Base de données

SQLite (`auth.db`), chemin configurable via `SOVEREIGN_AUTH_DB`. WAL mode activé pour la concurrence. Les sessions expirées sont nettoyées à chaque connexion. **Les sessions au format ancien (non-SHA-256) sont supprimées au démarrage** pour la sécurité.

### Validation des emails

Normalisation NFKC + minuscule + vérification des caractères de contrôle et zéro-largeur (empêche les comptes sosies visuels).

### Politique de mot de passe

- Minimum : 12 caractères
- Maximum : 72 octets (limite bcrypt)
- Appliquée via l'API et lors de la création du compte admin initial

### Compte admin initial

Créé depuis `ADMIN_EMAIL` et `ADMIN_PASSWORD` au premier démarrage. Si `ADMIN_PASSWORD` a moins de 12 caractères, le serveur **refuse de démarrer** (ValueError).

---

## Fichier 2 — `router.py` (endpoints publics)

### `POST /auth/login`

Throttle de connexion (en mémoire, thread-safe) :

| Compteur | Limite | Fenêtre |
|----------|--------|---------|
| Par client (IP) | 5 tentatives | 15 min |
| Par email | 20 tentatives | 15 min |

Le compteur est réservé **avant** le vérification bcrypt (empêche les rafales parallèles de passer la même vérification).

### `POST /auth/logout`

Supprime le token de la base. Idempotent (aucun effet si le token est déjà expiré).

### `GET /auth/me`

Vérifie la session et retourne `{id, email, role}`. Renvoie 401 si expiré.

---

## Fichier 3 — `users_router.py` (administration des comptes)

### Accès requis

Tous les endpoints `/auth/users` nécessitent le rôle `admin`. Le rôle est vérifié par `RequireRole("admin")` via la dépendance FastAPI.

### Protections importantes

| Protection | Description |
|------------|-------------|
| Dernier admin | Impossible de désactiver ou rétrograder le dernier administrateur actif (vérification en transaction IMMEDIATE) |
| Révocation des sessions | Désactiver un compte ferme toutes ses sessions |
| Clés par défaut | En production (`APP_ENV=production`), les clés par défaut de `.env.example` sont refusées |
| Réinitialisation de mot de passe | Ferme toutes les sessions du compte (sauf optionnellement la session courante) |
| Audit | Chaque action (création, modification, réinitialisation) est inscrite au journal |

### Changement de mot de passe (self-service)

`POST /auth/password` — disponible pour tout utilisateur connecté. Vérifie le mot de passe actuel, puis applique le nouveau. Throttle identique au login (5 tentatives, 15 min).

---

## Points de vigilance — décisions propriétaire requises

| # | Point | Décision |
|---|-------|----------|
| 1 | **TTL de session** : par défaut `SESSION_TTL_HOURS=24`. Réduire à 8h pour plus de sécurité, ou garder 24h pour le confort. | `SESSION_TTL_HOURS=__` dans `.env` |
| 2 | **bcrypt vs Argon2id** : bcrypt est sûr pour le MVP. Migration vers Argon2id possible sans casser les sessions (hachage progressif à la connexion). | Garder bcrypt ✓ ou planifier migration |
| 3 | **Récupération de compte admin** : si l'admin perd son mot de passe et qu'il est le seul admin, seule une intervention directe sur `auth.db` permet de réinitialiser. Accepté ? | Accepté ✓ ou documenter procédure |
| 4 | **Tokens en sessionStorage** (front mizanbi-client) : fermeture d'onglet = déconnexion. Comportement voulu ? | ✓ Oui (plus sûr) ou Non |

---

## Addendum P-083 — identité par personne (à relire séparément)

**Statut :** ⏳ relecture humaine requise (changement sensible dans `app/auth/` et `app/security/`).

### Ce qui change
| Élément | Comportement |
|---|---|
| Clés personnelles | `mzb_` + 32 octets aléatoires ; **seule l'empreinte SHA-256** est en base, avec un préfixe non secret (12 caractères). Affichée en clair **une fois** (création, rotation). Comparaison `hmac.compare_digest`. |
| Propriété | Une personne peut avoir jusqu'à 10 clés actives, chacune a un seul propriétaire. **Seul le propriétaire crée ou fait tourner** sa clé (session requise, jamais par une clé). L'administrateur peut **lister et révoquer**, pas créer. |
| Rôle | **Jamais copié dans la clé** : relu depuis l'utilisateur à chaque requête. Rétrogradation, désactivation, effacement de compte (P-064) et révocation jouent à la requête suivante ; aucun cache. |
| Durée de vie | 1 à 365 jours (90 par défaut), expiration obligatoire. « Dernière utilisation » écrite au plus une fois par minute. |
| Ce qu'une clé ouvre | lecture, import, lancement de calculs. **Ne l'ouvrent pas** : résolution d'anomalie (et plus tard revue, validation), gestion des comptes, gestion des clés → **session nominative** seulement. |
| Journal | Chaque événement porte `auth_method` (`session`, `api_key`, `legacy_key`), `key_id` et `key_ref` (préfixe non secret). L'acteur est `user:<id>` pour une personne, `legacy:<rôle>:<empreinte de 8 caractères>` pour une clé partagée (jamais un fragment de la clé). |
| Clés d'environnement | « Partagées (héritées) », non attribuables. **Échéance ferme** `SOVEREIGN_LEGACY_KEYS_DEADLINE` : après, refusées. En production : échéance obligatoire (≤ 180 jours), lecture seule par défaut, clés de test connues et valeurs par défaut **refusées au démarrage**. Avertissement au démarrage et `GET /auth/keys/legacy-status` (admin). |
| Sécurité par ligne | Une clé personnelle hérite des périmètres de son propriétaire (`Principal("user", id)`) ; une clé héritée reste `Principal("key")` (accès refusé aux tables protégées, comportement existant). |

### Première clé d'une automatisation
Un compte de service est un **compte nommé** : l'administrateur le crée (`POST /auth/users`), la personne responsable s'y connecte et crée la clé depuis cette session. Aucune commande d'amorçage, donc aucune création de clé hors session.

### Décisions à confirmer
| # | Décision | Choix proposé |
|---|---|---|
| 5 | Les clés héritées en lecture seule : **hors production**, le plafond est désactivé par défaut (les tests et le développement utilisent encore ces clés) ; en production il est actif par défaut. | ✓ Oui, ou plafond partout |
| 6 | Préfixe affiché pour une clé héritée : **empreinte SHA-256 de 8 caractères** plutôt que les premiers caractères de la clé (ne divulgue rien de la clé). | ✓ Oui |
| 7 | Le sous-système `X-Admin-Key` de `app/routers/admin.py` compare encore `SOVEREIGN_ADMIN_KEY` directement ; il n'est pas couvert par cette tâche. | À traiter (voir revue) |

## Checklist de validation

- [ ] Lu et compris par le propriétaire
- [ ] Paramètre `SESSION_TTL_HOURS` fixé dans `.env` de production
- [ ] `ADMIN_EMAIL` et `ADMIN_PASSWORD` (≥12 caractères) définis dans `.env` de production
- [ ] `APP_ENV=production` dans `.env` de production
- [ ] Choix bcrypt/Argon2id documenté dans `docs/adr/`
- [ ] Addendum P-083 relu ; `SOVEREIGN_LEGACY_KEYS_DEADLINE` fixée dans `.env` de production ; clés de test absentes

---

**Signé :** ____________________________  **Date :** ___________

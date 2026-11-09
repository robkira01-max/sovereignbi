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

## Checklist de validation

- [ ] Lu et compris par le propriétaire
- [ ] Paramètre `SESSION_TTL_HOURS` fixé dans `.env` de production
- [ ] `ADMIN_EMAIL` et `ADMIN_PASSWORD` (≥12 caractères) définis dans `.env` de production
- [ ] `APP_ENV=production` dans `.env` de production
- [ ] Choix bcrypt/Argon2id documenté dans `docs/adr/`

---

**Signé :** ____________________________  **Date :** ___________

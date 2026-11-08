# Politique de sécurité MizanBI

## 1. Modèle de menace

MizanBI est conçu pour être déployé **en réseau local ou en cloud privé**. Les données analytiques de l'entreprise ne quittent jamais le périmètre contrôlé.

Menaces principales :
- Exfiltration de données via injection SQL dans les requêtes IA
- Accès non autorisé aux routes d'administration
- Fuite de données si le conteneur est compromis
- Injection de prompt via les données sources

## 2. Contrôle d'accès (RBAC)

Trois rôles, hiérarchiques :

| Rôle | Clé API (`X-Api-Key`) | Routes accessibles |
|---|---|---|
| `viewer` | `SOVEREIGN_VIEWER_KEY` | `/health`, `/ask`, `/upload`, `/export/*`, dashboards (lecture), `GET /semantic/*` |
| `editor` | `SOVEREIGN_EDITOR_KEY` | Tout viewer + dashboards (écriture), `/feedback`, activation de secteur (`/semantic/sectors/*`) |
| `admin` | `SOVEREIGN_ADMIN_KEY` | Tout + `/admin/*` (modèle sémantique, propositions, rapport) |

Deux formes d'authentification : clé API (intégrations) ou session `Authorization: Bearer` (connexion web). Une session porte le **rôle du compte** (`users.role`, défaut `viewer`) ; il n'y a plus d'élévation automatique en `admin`. Un rôle inconnu en base est refusé (403). Les clés API sont comparées en temps constant.

**Rotation des clés** : générer de nouvelles clés avec `openssl rand -hex 32`, mettre à jour `.env`, redémarrer le service.

### Connexion et sessions

- Mots de passe : bcrypt, 12 tours. Un mot de passe de plus de 72 octets est refusé de la même façon qu'un mauvais mot de passe (pas d'erreur 500 qui révélerait l'existence du compte). Le chemin « compte inconnu » exécute un contrôle de même coût.
- Verrouillage : 5 échecs / 15 min par couple (e-mail, client) et 20 échecs / 15 min par e-mail, comptés avant la vérification du mot de passe (une rafale parallèle ne contourne pas la limite). L'e-mail est comparé sans tenir compte de la casse, comme en base.
- Sessions : jeton aléatoire de 256 bits, **seul son hachage SHA-256 est stocké** ; expiration `SESSION_TTL_HOURS` (défaut 24 h), sessions expirées purgées à la connexion, session invalide dès que le compte est désactivé.
- Limitation de débit : par IP cliente (IPv6 regroupé par /64). `X-Forwarded-For` n'est pris en compte que si l'appelant TCP est dans `SOVEREIGN_TRUSTED_PROXIES` (`private` par défaut, liste de CIDR, ou `none` si le port est publié sans proxy), lu de droite à gauche.

## 3. Isolation SQL (sql_guard)

Toutes les requêtes générées par l'IA passent par `app/security/sql_guard.py` avant exécution :

- Une seule instruction par requête
- SELECT uniquement (INSERT/UPDATE/DELETE/DROP bloqués)
- Tables en liste blanche uniquement
- Fonctions de lecture de fichiers système bloquées (`read_csv`, `read_parquet`, etc.)
- Appels réseau DuckDB bloqués (pas de `httpfs`)
- LIMIT forcé à 1 000 lignes

## 4. Isolation réseau

- Le conteneur Ollama est sur un réseau Docker `internal` (pas d'accès Internet)
- L'API n'émet aucun appel vers l'extérieur (vérifié par `tests/test_no_external_calls_in_app.py`)
- Système de fichiers du conteneur API en lecture seule (`read_only: true`), seul `/tmp` est accessible en écriture

## 5. Secrets

- Aucune clé ni secret dans le code source ou les images Docker
- Toutes les clés via variables d'environnement (`.env`, jamais commité)
- `.gitignore` exclut `.env` et `.env.*`

## 6. Injection de prompt

L'IA génère du SQL à partir des questions des utilisateurs. Un contenu malveillant dans les données (cellules Excel, noms de colonnes) pourrait tenter d'influencer le LLM. La défense est le `sql_guard` : même si le LLM "obéit" à une instruction malveillante, le SQL résultant est rejeté s'il sort des règles.

**Ce qui n'est pas protégé** : un LLM très obéissant qui génère un SELECT valide sur une mauvaise table — raison pour laquelle la liste blanche de tables est stricte.

## 7. Journalisation

- Les actions d'audit sont enregistrées dans `data/audit.jsonl` (chaîne SHA-256)
- Aucune donnée sensible n'est loguée (les payloads ne sont pas journalisés)

## 8. Mises à jour

- Mettre à jour l'image Ollama régulièrement : `docker compose pull ollama`
- Surveiller les CVE sur les dépendances Python : `pip-audit` (non inclus dans le projet, à lancer manuellement)
- Le SBOM est générable avec `python tools/generate_sbom.py`

## 9. Contact

Pour signaler une vulnérabilité : contacter directement l'administrateur système. Ce projet est en phase pilote — pas de programme de divulgation public.

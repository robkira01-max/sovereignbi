# Politique de sécurité SovereignBI

## 1. Modèle de menace

SovereignBI est conçu pour être déployé **en réseau local ou en cloud privé**. Les données analytiques de l'entreprise ne quittent jamais le périmètre contrôlé.

Menaces principales :
- Exfiltration de données via injection SQL dans les requêtes IA
- Accès non autorisé aux routes d'administration
- Fuite de données si le conteneur est compromis
- Injection de prompt via les données sources

## 2. Contrôle d'accès (RBAC)

Trois rôles, hiérarchiques :

| Rôle | Header | Routes accessibles |
|---|---|---|
| `viewer` | `X-Api-Key: SOVEREIGN_VIEWER_KEY` | `/health`, `/ask`, `/upload`, `/export/*`, dashboards (lecture) |
| `editor` | `X-Api-Key: SOVEREIGN_EDITOR_KEY` | Tout viewer + dashboards (écriture), `/feedback` |
| `admin` | `X-Admin-Key: SOVEREIGN_ADMIN_KEY` | Tout + `/admin/*` (modèle sémantique, propositions, rapport) |

**Rotation des clés** : générer de nouvelles clés avec `openssl rand -hex 32`, mettre à jour `.env`, redémarrer le service.

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

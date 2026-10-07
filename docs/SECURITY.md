# Politique de sécurité — SovereignBI

## Signalement d'une vulnérabilité

Si vous découvrez une vulnérabilité de sécurité dans SovereignBI, merci de **ne pas** ouvrir une issue publique.

Envoyez un rapport privé à : **roblehassanabdi@gmail.com**

Incluez :
- Description de la vulnérabilité
- Étapes de reproduction
- Impact estimé (CVSS si possible)
- Suggestion de correction (optionnel)

Vous recevrez un accusé de réception sous 48 heures. Les vulnérabilités critiques sont corrigées sous 7 jours.

---

## Architecture de sécurité

### Principe directeur : souveraineté des données

SovereignBI est conçu pour fonctionner **100 % en local**. Aucune donnée ne quitte votre infrastructure, sauf si vous configurez explicitement un connecteur externe (Snowflake, BigQuery).

### Contrôle d'accès (RBAC)

| Rôle    | Accès autorisé                       |
|---------|--------------------------------------|
| viewer  | Lecture seule — requêtes, exports    |
| editor  | Création de templates, import données|
| admin   | Administration complète              |

Authentification via `X-Api-Key` (en-tête HTTP). Les clés sont lues depuis les variables d'environnement à l'appel ; elles ne sont jamais stockées en clair dans le code.

### Rate limiting

Fenêtre glissante de 60 rpm par adresse IP (configurable via `SOVEREIGN_RATE_LIMIT_RPM`). Les endpoints de santé (`/health`, `/live`, `/ready`, `/metrics`) sont exemptés. En-têtes `X-RateLimit-Limit/Remaining/Reset` présents sur chaque réponse.

### En-têtes de sécurité

Chaque réponse inclut :
- `Strict-Transport-Security: max-age=63072000; includeSubDomains`
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Content-Security-Policy: default-src 'self'; ...`
- `Referrer-Policy: strict-origin-when-cross-origin`

### Exécution SQL

Toutes les requêtes SQL passent par `sql_guard` (sqlglot) :
- SELECT uniquement (INSERT/UPDATE/DELETE/DROP bloqués)
- Whitelist de tables autorisées
- `LIMIT` forcé à 10 000 lignes maximum
- Fonctions de lecture de fichiers interdites (`read_csv`, `parquet_scan`, etc.)

DuckDB exécuté avec `enable_external_access: False` — aucun accès réseau ni fichier système.

### Audit de configuration

À chaque démarrage, SovereignBI vérifie :
- **SEC-001 (critique)** — `SOVEREIGN_ADMIN_KEY` non par défaut
- **SEC-002 (critique)** — `SOVEREIGN_EMBED_SECRET` ≥ 32 caractères
- **SEC-003 (élevé)** — Rate limit raisonnable en production
- **SEC-004 (élevé)** — `DEBUG` désactivé en production
- **SEC-005 (moyen)** — Ollama non exposé sur IP publique
- **SEC-006 (info)** — Clés viewer et editor distinctes

---

## Variables d'environnement sensibles

| Variable                  | Rôle                         | Jamais committer |
|---------------------------|------------------------------|------------------|
| `SOVEREIGN_ADMIN_KEY`     | Clé admin RBAC               | ✓                |
| `SOVEREIGN_EDITOR_KEY`    | Clé editor RBAC              | ✓                |
| `SOVEREIGN_VIEWER_KEY`    | Clé viewer RBAC              | ✓                |
| `SOVEREIGN_EMBED_SECRET`  | Signature tokens embed HMAC  | ✓                |
| `SOVEREIGN_DB_*`          | Credentials connecteurs       | ✓                |

Copier `.env.example` vers `.env` et remplir les valeurs. Le fichier `.env` est dans `.gitignore`.

---

## Conformité

- **Loi 25 (Québec)** — données traitées localement, pas de transfert hors Québec par défaut
- **PIPEDA (Canada)** — consentement, finalité limitée, accès sécurisé
- Rapport de conformité disponible via `GET /v1/compliance/report` (rôle admin)

---

## Historique des corrections

| Version | Sévérité | Description                              |
|---------|----------|------------------------------------------|
| 1.0.0   | N/A      | Version initiale — audit démarrage ajouté|

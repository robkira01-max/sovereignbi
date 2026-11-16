# Checklist de mise en service — MizanBI

> À cocher pour **chaque installation** avant l'arrivée de données réelles. Chaque case donne une commande ou un contrôle vérifiable. Remplacez `$HOST` par l'adresse du serveur, `$ADMIN_KEY` par la clé administrateur. Si un contrôle échoue, **ne pas mettre en service**.

## 0. Décisions préalables (sans elles, le reste est du travail perdu)
- [ ] Hébergeur et région choisis et notés dans le DPA (annexe A).
- [ ] Fournisseur d'IA choisi : ☐ modèle local ☐ externe + mode strict ☐ externe sans strict (décision écrite du client) — annexe D du DPA remplie et signée.
- [ ] DPA validé par un juriste ; pages légales renseignées (`mizanbi-client/src/lib/legalConfig.ts`, puis `draft: false`).
- [ ] Revue de sécurité : relecture du propriétaire faite pour la sécurité par ligne, la suppression de compte et l'authentification (règle du dépôt).
- [ ] Test d'intrusion par un tiers réalisé **avant** toute donnée réelle.

## 1. Secrets et accès
- [ ] Clés générées avec `openssl rand -hex 32` pour `SOVEREIGN_VIEWER_KEY`, `SOVEREIGN_EDITOR_KEY`, `SOVEREIGN_ADMIN_KEY`, `SOVEREIGN_EMBED_SECRET`, `SOVEREIGN_CERT_SECRET` (obligatoire en production) ; aucune valeur de `.env.example` conservée.
- [ ] `.env` absent du dépôt et lisible seulement par le compte de service : `git check-ignore .env` répond `.env`.
- [ ] Compte administrateur créé avec un mot de passe fort (12 caractères minimum, unique) ; `ADMIN_PASSWORD` retiré de `.env` après la création.
- [ ] Journal de démarrage lu : **aucun avertissement `critical`** (clé par défaut, secrets absents) et aucun avertissement `SOVEREIGN_AI_STRICT`.
- [ ] `SOVEREIGN_CORS_ORIGINS` limité aux adresses réelles de l'application.

## 2. IA
- [ ] `LLM_PROVIDER` conforme à la décision (section 0). Avec `kimi` : `KIMI_BASE_URL` en `https://`, `KIMI_API_KEY`, `KIMI_MODEL`, `KIMI_DAILY_BUDGET_USD` définis.
- [ ] Contrôle de ce qui est annoncé aux utilisateurs : `curl -s -H "X-Api-Key: $VIEWER_KEY" https://$HOST/compliance/notice` montre `ai_provider`, `ai_external` et `ai_strict_mode` conformes au DPA ; la pastille de l'en-tête affiche le même état.
- [ ] Avec un fournisseur externe : `ai_strict_mode` est `true` (sauf décision écrite contraire consignée dans l'annexe D, D.5).
- [ ] Avec le modèle local : un serveur adapté (GPU) est en place ; sinon les réponses mettent plusieurs minutes.
- [ ] Précision SQL du modèle retenu mesurée (`python -m eval.compare_strict`, voir `eval/BASELINE.md`) et résultat noté. **Cette mesure n'a pas encore été faite.**

## 3. Données et accès par ligne
- [ ] Données de test **fictives** chargées d'abord ; aucune donnée réelle avant la fin de la recette (section 9).
- [ ] Si des périmètres sont nécessaires : `data/row_policies.yaml` écrit (modèle : `data/row_policies.example.yaml`) et `GET /security/row-policies` renvoie `valid: true` et aucun `problem`.
- [ ] Chaque compte non administrateur a ses périmètres (`PUT /security/users/{id}/scopes/{scope}`) ; un compte sans périmètre ne voit **rien** des tables protégées : vérifié avec un compte de test.
- [ ] Rappel : les clés API viewer/editor et les jetons de partage ne voient aucune table protégée ; les bulletins par courriel sont refusés sur ces tables.

## 4. Courriel (si les abonnements sont utilisés)
- [ ] `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` définis ; `SOVEREIGN_PUBLIC_URL` en `https://` (sans lui, pas de lien de désabonnement).
- [ ] `GET /subscriptions/status` indique `smtp_configured: true` (sinon aucun courriel réel n'est envoyé).
- [ ] Envoi d'essai vers **votre propre adresse** (`POST /subscriptions/{id}/send-now`), message reçu, lien de désabonnement fonctionnel. **Jamais testé contre un vrai serveur SMTP à ce jour.**
- [ ] `SOVEREIGN_SUBSCRIPTION_DOMAINS` défini si les destinataires doivent être limités à un domaine.

## 5. Conformité
- [ ] Rôles du DPA répartis : le client est responsable du traitement des données importées ; l'éditeur l'est des comptes et du journal.
- [ ] Consentement des destinataires des bulletins : responsabilité du client, rappelée dans l'interface ; à confirmer par écrit.
- [ ] Procédures de suppression/export de compte connues de l'administrateur : `GET /compliance/account/{id}/export`, `DELETE /compliance/account/{id}`.

## 6. Journal d'audit et incidents
- [ ] `GET /audit/verify` répond `valid: true` ; **noter `entries` et `head` hors du serveur** (ancrage) et la date.
- [ ] Une personne désignée connaît `docs/incident-procedure.md` ; registre prêt (`GET /compliance/incidents`).
- [ ] Contact et délai de notification des incidents convenus avec le client (72 h au plus, DPA §8).

## 7. Sauvegardes
- [ ] Sont sauvegardés : `data/` (`audit.jsonl`, `certified_datasets.json`, `subscriptions.json`, `incidents.jsonl`, tableaux de bord…), la base d'authentification (`SOVEREIGN_AUTH_DB`), `.env` (coffre séparé), le volume DuckDB si `SOVEREIGN_DB_PATH` est défini.
- [ ] Les sauvegardes sont chiffrées et stockées hors du serveur.
- [ ] **Une restauration a été testée de bout en bout sur une machine vierge.** Elle n'a jamais été testée à ce jour : tant qu'elle ne l'est pas, ne pas annoncer d'objectif de reprise (RTO/RPO) au client.

## 8. Réseau
- [ ] Application servie en HTTPS uniquement, redirection HTTP→HTTPS, HSTS actif.
- [ ] Aucun port d'API publié sans proxy de confiance ; `SOVEREIGN_TRUSTED_PROXIES` réglé (`none` si le port est publié sans proxy).
- [ ] Pour un déploiement hors ligne : contrôle de non-sortie réseau fait (`docs/deploiement.md`, section « Isolation réseau »).
- [ ] Chiffrement du disque activé (`docs/deploiement.md`).
- [ ] Lighthouse lancé sur l'URL publique ; `VITE_API_BASE` et `VITE_SITE_URL` renseignés au moment de la construction du client.

## 9. Recette (avec les données fictives)
- [ ] Connexion avec un compte de chaque rôle (viewer, editor, admin) : chacun ne voit que ce que son rôle permet.
- [ ] Question en langage naturel → réponse avec le SQL visible ; refus d'une requête dangereuse.
- [ ] Import CSV, import SDMX-CSV (« Vérifier » puis « Charger »), export SDMX d'une tuile.
- [ ] Une table marquée « validée » : la pastille passe à « modifiée depuis la validation » dès qu'on change les données.
- [ ] Bulletin HTML/PPTX d'un tableau de bord ; abonnement (section 4).
- [ ] Après la recette : les données de test sont supprimées, `GET /audit/verify` est refait et un nouvel ancrage est noté.

## 10. Après la mise en service
- [ ] Vérification hebdomadaire de `GET /audit/verify` avec l'ancrage précédent.
- [ ] Rotation des clés et mots de passe selon la politique du client.
- [ ] Revue des avertissements de démarrage à chaque mise à jour ; mise à jour des dépendances (`pip-audit`, non inclus, à lancer à la main).
- [ ] Revue du DPA et des sous-traitants à chaque changement de fournisseur ou de modèle (annexe D, D.5).

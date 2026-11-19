# Contrôles d'audit (P-075)

Dix règles déterministes, en SQL, **sans IA**. Chaque signalement renvoie à une règle et à sa version.
Formulation : « signal de risque à examiner », jamais « fraude » ; un signalement n'est pas une conclusion.

## Utilisation

1. Déposer et importer un fichier (P-074, `/audit-data`).
2. `GET /audit-rules/rules` : règles, paramètres, interprétation.
3. `POST /audit-rules/runs` `{document_id, rules?, params?}` (éditeur). Les règles dont les données ou paramètres manquent
   sont `not_applicable` avec la raison — jamais « aucun problème » par défaut.
4. `GET /audit-rules/runs/{id}` et `/findings` (éditeur ; l'auteur du run et l'admin seulement).

## Règles

| Code | Contrôle | Gravité | Paramètres |
|---|---|---|---|
| AUD001 | Lignes strictement identiques (référence, date, compte, montant, devise) | warning | — |
| AUD002 | Même montant/compte/devise à des dates ou références différentes, fenêtre courte | info | `window_days` (7) |
| AUD003 | Dépenses > budget, ou compte sans budget | warning | `budgets` **obligatoire** |
| AUD004 | Écriture un jour de repos (**indicatif**, pas une irrégularité) | info | `weekend_days` ([6,7] ; Djibouti : [5,6]) |
| AUD005 | Fractionnement potentiel sous un seuil | warning | `threshold` **obligatoire**, `window_days` (3) |
| AUD006 | Montant inhabituel (score z) | info | `z_threshold` (3), `min_count` (8) |
| AUD007 | Coordonnées bancaires communes | warning | **non applicable** : aucun champ bancaire importé |
| AUD008 | Dépense sans référence de pièce | warning | — |
| AUD009 | Écriture hors exercice / période | warning | `period_start`, `period_end` |
| AUD010 | Écriture déséquilibrée (débits ≠ crédits par référence) | warning | colonnes débit/crédit requises |

## Garde-fous

- Les lignes en erreur d'import (`has_error`) sont exclues des règles et comptées dans le résumé du run.
- Un seuil ou un budget n'est jamais supposé : il est fourni, ou la règle est `not_applicable`.
- Plafond de 500 signalements par règle (`truncated` indique le dépassement).
- Avec des règles de sécurité par ligne actives, l'exécution et la lecture sont réservées à l'admin.
- AUD007 : quand un champ de coordonnées bancaires existera, masquage par défaut, accès éditeur/admin, mention au registre
  de vie privée et au DPA **avant** activation.
- Modifier une règle = ajouter une version (nouveau `version`), jamais réécrire l'ancienne silencieusement.

## Limites

Pertinence non validée par un utilisateur réel (D-5) ; seuils par défaut indicatifs ; calcul sur un seul fichier.

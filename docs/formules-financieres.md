# Formules financières versionnées (P-073)

Premier module du pack optionnel « Audit » (P-073 à P-077). Il calcule des indicateurs budgétaires et de recettes
de façon **reproductible** : chaque résultat renvoie à une formule identifiable, une version, des données sources,
une version du moteur et un hash.

## Ce que le module garantit

- Calcul en `decimal.Decimal` (précision 50), jamais en flottant. Les montants entrent et sortent en **chaînes**.
- Arrondi explicite, propre à la formule (`precision` + `rounding`). La valeur non arrondie est conservée (`raw_value`).
- Division par zéro, valeur manquante, valeur négative, variable inconnue : **erreur explicite** (HTTP 422 avec un code),
  jamais un 0 ou un NaN silencieux. Une formule peut déclarer `on_zero_division: null` : le résultat est alors
  « indéfini » et le dit.
- Même formule, même version, mêmes entrées, même moteur ⇒ même `result_hash` (les `run_id` diffèrent).
- Modifier une formule = **ajouter une version**. Les anciennes restent consultables et recalculables.

## Ce qu'il ne garantit pas

- Il ne vérifie pas que les données sources sont justes (c'est le rôle de P-074, contrôle qualité).
- Le chat n'appelle le moteur que dans le cas décrit ci-dessous (« Chat et formules »). Tout autre chiffre du chat
  reste **exploratoire** (text-to-SQL, requête visible).
- La pastille « calculé » (P-069) n'est pas encore branchée sur les runs.

## Chat et formules (P-080)

Une mesure de `semantic/model.yaml` peut déclarer une formule et lier ses variables à des colonnes :

```yaml
- name: "taux d'exécution budgétaire"
  aliases: ["exécution du budget"]
  sql: "SUM(realise) / SUM(vote)"        # chemin exploratoire, jamais utilisé quand la formule répond
  tables: ["budget"]
  formula: BUD001
  formula_inputs:                        # variable de la formule → somme d'une colonne numérique
    depenses: {table: budget, column: realise}
    budget_vote: {table: budget, column: vote}
```

Comportement (`app/pipeline/formula_route.py`, aucun modèle de langage dans cette étape) :

- **Reconnaissance déterministe** (résolveur sémantique P-065). Une seule formule reconnue → le moteur calcule ; aucune ou
  plusieurs → réponse **exploratoire** (on ne choisit pas dans le doute).
- Réponse « **Calculé** » : formule, version, run, lien « Voir le calcul » (écran Formules). Même chemin de calcul que
  `POST /financial/runs` : mêmes entrées ⇒ même `result_hash`.
- **Paramètres manquants** (variable obligatoire sans `formula_inputs`) : le chat dit ce qui manque et ne calcule pas.
  Les valeurs écrites dans la question ne sont **pas** lues : on ne devine pas.
- **Division par zéro, table vide, colonne absente** : message explicite, pastille « Calcul non effectué », aucun chiffre.
- **Rôles** : lancer un calcul est réservé aux éditeurs/admin (comme `/financial/runs`) ; un viewer reçoit un refus explicite.
- Chaque calcul par le chat est inscrit au journal (`financial_run` avec `via=chat`, puis `chat_formula_answer`).
- Les exports Excel/PDF d'une réponse du chat portent la mention « Exploratoire, non certifié ».
- Vérification : `.venv/bin/python -m eval.run_formula_routing` (11 cas déterministes) ; `GET /semantic/validate` contrôle
  que la formule et les variables existent. **Aucune précision de reconnaissance sur des formulations libres n'est annoncée** :
  elle dépend des synonymes déclarés ; la précision du text-to-SQL exploratoire par modèle relève de P-078.

## Ajouter ou modifier une formule

Les formules sont dans `rules/financial/<code en minuscules>.yaml` (un fichier par formule). Le registre se recharge
tout seul quand un fichier change ; une définition invalide fait échouer le chargement avec un message précis.

```yaml
code: BUD001                  # A-Z, chiffres, _ ; le fichier s'appelle bud001.yaml
family: budget
versions:
  - version: 1                # 1, 2, 3… sans trou
    label: "Taux d'exécution budgétaire"
    expression: "depenses / budget_vote * 100"   # + - * /, parenthèses, max(), min(), abs()
    result_unit: "%"
    precision: 2              # 0 à 10 décimales
    rounding: ROUND_HALF_UP   # ou ROUND_HALF_EVEN, ROUND_DOWN, ROUND_FLOOR, ROUND_CEILING
    on_zero_division: error   # ou null
    variables:
      depenses:   {label: "Dépenses réalisées", unit: "monnaie", required: true, allow_negative: false}
      budget_vote: {label: "Budget voté", unit: "monnaie"}
```

Pour changer le calcul : **ajouter** une entrée `version: 2` ; ne pas éditer la version 1. Le `definition_hash`
couvre ce qui change le résultat (expression, variables, unités, précision, arrondi, règle de division par zéro),
pas les libellés. Si une version existante est modifiée « en place », les anciens runs affichent
`definition_status: definition_changed`.

Une variable facultative (`required: false`) doit déclarer un `default` explicite.

## API

| Route | Rôle | Rôle de la route |
|---|---|---|
| `GET /financial/formulas[?all_versions=true&family=]` | viewer | Liste (dernière version par défaut) |
| `GET /financial/formulas/{code}[?version=]` | viewer | Détail et historique des versions |
| `POST /financial/runs` | editor | Lance un calcul |
| `GET /financial/runs[?formula_code=&limit=&offset=]` | viewer | Historique |
| `GET /financial/runs/{id}` | viewer | Détail, entrées, provenance, `definition_status` |
| `GET /financial/runs/{a}/compare/{b}` | viewer | Différences d'entrées et écart de valeur |

Corps de `POST /financial/runs` :

```json
{"formula_code": "BUD001", "version": 1,
 "inputs": {"budget_vote": "120000000"},
 "from_table": {"depenses": {"table": "execution_2026", "column": "montant", "agg": "sum"}}}
```

- `inputs` : valeurs explicites, en chaînes décimales (les flottants JSON sont refusés).
- `from_table` : somme d'une colonne, lue par `DataStore.execute` (sécurité par ligne). Colonnes entières ou
  `DECIMAL` : somme exacte. Colonnes flottantes : converties en `DECIMAL(38,6)` avant la somme, ce qui est
  consigné dans `sources` du run. Autres types : refusés. Une somme nulle (aucune ligne) est une valeur
  manquante, pas un zéro.

## Stockage et audit

- Tables DuckDB `audit_analysis_runs` et `audit_calculation_results`, jamais modifiées par ce module.
- Journal chaîné (P-071) : `financial_run` et `financial_run_rejected`, avec identifiants et hash seulement,
  **aucune valeur de donnée**.

## Bibliothèque livrée (version 1)

Budget : BUD001 taux d'exécution, BUD002 dépassement, BUD003 taux de dépassement, BUD004 écart budget/réalisé,
BUD005 écart relatif, BUD006 solde disponible, BUD007 taux d'engagement, BUD008 taux de paiement.
Recettes : REC001 taux de recouvrement, REC002 écart de recettes, REC003 reste à recouvrer.
Les autres familles (dette, trésorerie, performance, comparaison) viendront dans des propositions ultérieures.

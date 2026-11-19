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
- Le chat n'appelle pas encore le moteur : une mesure sémantique peut pointer vers une formule (`formula: BUD001`,
  validé par `GET /semantic/validate`), mais le pipeline text-to-SQL continue de générer son propre SQL.
  Un chiffre issu du chat doit donc être considéré comme **exploratoire** tant que cette liaison n'est pas faite.
- La pastille « calculé » (P-069) n'est pas encore branchée sur les runs.

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

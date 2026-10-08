# SovereignBI — Add-in Excel

Analysez vos données Excel directement depuis un panneau latéral, sans quitter Excel.

## Prérequis

- Excel 2016+ (Windows/Mac) ou Excel Online (Microsoft 365)
- SovereignBI en cours d'exécution (`uvicorn app.main:app --port 9000`)
- Une clé API (viewer ou editor)

## Installation du complément

### Excel Desktop (Windows/Mac)

1. Ouvrir Excel
2. `Insertion` → `Mes compléments` → `Gérer les autres compléments`
3. Cliquer `Parcourir...` → sélectionner `frontend/excel-addin/manifest.xml`
4. Le bouton **Analyser** apparaît dans l'onglet `Accueil`

### Excel Online

1. Ouvrir un classeur sur office.com
2. `Insertion` → `Compléments Office` → `Charger un complément`
3. Uploader `frontend/excel-addin/manifest.xml`

## Configuration

À la première ouverture du panneau :

1. Cliquer sur `⚙️ Paramètres` (en bas du panneau)
2. **URL de l'API** : `http://localhost:9000` (ou l'URL de votre serveur)
3. **Clé API** : votre clé viewer ou editor
4. Cliquer `💾 Sauvegarder`

## Utilisation

```
┌─────────────────────────────┐
│ ⚡ SovereignBI              │
│ IA locale · vos données...  │
├─────────────────────────────┤
│ 1. DONNÉES                  │
│ [📤 Envoyer la feuille]     │
│ ✅ Table "feuil1" chargée   │
├─────────────────────────────┤
│ 2. QUESTION                 │
│ ┌─────────────────────────┐ │
│ │ Quel est le total par   │ │
│ │ région ?                │ │
│ └─────────────────────────┘ │
│ [🔍 Demander]               │
├─────────────────────────────┤
│ 3. RÉSULTATS                │
│ Le total par région est...  │
│ ┌────────┬────────┐         │
│ │ Région │ Total  │         │
│ │ Nord   │ 1 234  │         │
│ │ Sud    │ 5 678  │         │
│ └────────┴────────┘         │
│ [📥 Insérer dans Excel]     │
└─────────────────────────────┘
```

### Étape 1 — Envoyer les données

- Sélectionnez votre plage de données (ou laissez Excel détecter la plage utilisée)
- Cliquez **📤 Envoyer la feuille active**
- La première ligne doit contenir les en-têtes de colonnes
- Maximum : 10 000 lignes × 500 colonnes

### Étape 2 — Poser une question

Exemples de questions :
- "Combien de personnes au total ?"
- "Quel est le total des ventes par mois ?"
- "Quels sont les 5 pays avec le plus d'enregistrements ?"
- "Quel est le pourcentage de femmes ?"

### Étape 3 — Insérer les résultats

- Cliquez **📥 Insérer dans Excel** pour coller les résultats sous vos données
- Les colonnes et lignes sont insérées automatiquement

## Endpoints API

| Endpoint | Méthode | Description |
|---|---|---|
| `/api/v1/addin/push-data` | POST | Charge les données de la feuille |
| `/api/v1/addin/ask` | POST | Pose une question sur les données |
| `/api/v1/addin/status` | GET | État de l'add-in (tables chargées) |

## Sécurité

- Les données restent sur votre serveur local — aucun envoi externe
- Authentification par clé API (X-Api-Key)
- CORS configuré pour Excel Online (`excel.officeapps.live.com`)
- Les mots de passe de connexion DB ne transitent jamais par l'add-in

## Dépannage

| Problème | Solution |
|---|---|
| "Clé API manquante" | Vérifier les paramètres → clé API |
| "Aucune donnée chargée" | Cliquer "Envoyer la feuille active" d'abord |
| "Erreur réseau" | Vérifier que SovereignBI tourne sur le bon port |
| "Le pipeline LLM n'est pas disponible" | Lancer Ollama : `ollama serve` |

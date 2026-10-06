# Décision : moteur de dashboards (Sprint 4)

**Date :** 2026-10-06
**Décision : moteur maison** (spec YAML + Plotly + renderer léger)

## Critères évalués

| Critère | Superset (Apache 2.0) | Moteur maison |
|---|---|---|
| Thèmes par client | Partiel (CSS custom) | Natif (DashboardTheme) |
| Import/export templates | Non natif | YAML portable |
| RBAC / isolation client | RLS Superset (complexe) | Scopes simples |
| sql_guard intégré | Contournement possible | Obligatoire |
| Poids de maintenance | Élevé (Docker séparé) | Faible |
| Délai intégration | 2–3 semaines | 1 semaine |

## Conclusion

Superset écarté pour le MVP. Aucune tuile ne peut contourner `sql_guard` avec le moteur
maison (`render_tile` appelle systématiquement `validate_sql`).

Réévaluer à Sprint 6 si les besoins de visualisation dépassent Plotly.

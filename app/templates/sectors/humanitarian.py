"""Dashboard templates for humanitarian operations (UNHCR/IOM/WFP/OCHA)."""

HUMANITARIAN_TEMPLATES: list[dict] = [
    {
        "template_id": "tmpl-hum-beneficiaries",
        "title": "Tableau de bord bénéficiaires",
        "description": (
            "Vue d'ensemble des bénéficiaires enregistrés : total, répartition par statut "
            "(réfugié / PDI / demandeur d'asile), par pays d'origine et par site."
        ),
        "tags": ["humanitaire", "bénéficiaires", "unhcr", "iom", "hxl"],
        "sector": "humanitarian",
        "tiles": [
            {
                "type": "kpi",
                "title": "Total bénéficiaires",
                "question": "Combien y a-t-il de bénéficiaires enregistrés au total ?",
                "metric": "total_beneficiaires",
            },
            {
                "type": "bar",
                "title": "Bénéficiaires par statut de protection",
                "question": "Répartis les bénéficiaires par statut de protection.",
                "group_by": "statut_protection",
            },
            {
                "type": "bar",
                "title": "Top 10 pays d'origine",
                "question": "Quels sont les 10 principaux pays d'origine des bénéficiaires ?",
                "group_by": "pays_origine",
                "limit": 10,
            },
            {
                "type": "kpi",
                "title": "Personnes déplacées internes (PDI)",
                "question": "Combien y a-t-il de personnes déplacées internes ?",
                "metric": "deplaces_internes",
            },
            {
                "type": "kpi",
                "title": "Réfugiés enregistrés",
                "question": "Combien de bénéficiaires ont le statut réfugié ?",
                "metric": "refugies",
            },
        ],
    },
    {
        "template_id": "tmpl-hum-distributions",
        "title": "Suivi des distributions",
        "description": (
            "Opérations de distribution humanitaire : quantités distribuées, "
            "couverture par site, tendance mensuelle."
        ),
        "tags": ["humanitaire", "distribution", "wfp", "nfi", "hxl"],
        "sector": "humanitarian",
        "tiles": [
            {
                "type": "kpi",
                "title": "Total distributions réalisées",
                "question": "Combien d'opérations de distribution ont été réalisées ?",
                "metric": "total_distributions",
            },
            {
                "type": "kpi",
                "title": "Quantité totale distribuée (kg)",
                "question": "Quelle est la quantité totale distribuée en kg ?",
                "metric": "quantite_distribuee",
            },
            {
                "type": "bar",
                "title": "Distributions par type d'assistance",
                "question": "Répartis les distributions par type d'assistance.",
                "group_by": "type_assistance",
            },
            {
                "type": "line",
                "title": "Tendance mensuelle des distributions",
                "question": "Montre la tendance mensuelle du nombre de distributions.",
                "x": "date_distribution",
                "agg": "month",
            },
        ],
    },
    {
        "template_id": "tmpl-hum-displacement",
        "title": "Suivi des déplacements de population",
        "description": (
            "Mouvements de population : déplacements internes, flux transfrontaliers, "
            "retours, répartition par cause."
        ),
        "tags": ["humanitaire", "déplacement", "pdi", "dtm", "iom", "hxl"],
        "sector": "humanitarian",
        "tiles": [
            {
                "type": "kpi",
                "title": "Total personnes déplacées",
                "question": "Combien de personnes ont été déplacées au total ?",
                "sql": "SELECT SUM(nb_personnes) FROM deplacements",
            },
            {
                "type": "bar",
                "title": "Déplacements par type",
                "question": "Répartis les déplacements par type (interne, transfrontalier, retour).",
                "group_by": "type_deplacement",
            },
            {
                "type": "bar",
                "title": "Causes de déplacement",
                "question": "Quelles sont les principales causes de déplacement ?",
                "group_by": "cause",
            },
        ],
    },
]

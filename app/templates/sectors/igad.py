"""Dashboard templates for IGAD regional economic data."""

IGAD_TEMPLATES: list[dict] = [
    {
        "template_id": "tmpl-igad-economy",
        "title": "Tableau de bord économique IGAD",
        "description": (
            "Indicateurs macro-économiques de la région IGAD (Corne de l'Afrique) : "
            "PIB, croissance, inflation, IDE, dette publique."
        ),
        "tags": ["igad", "économie", "pib", "afrique-de-l-est", "banque-mondiale"],
        "sector": "igad_economic",
        "tiles": [
            {
                "type": "kpi",
                "title": "PIB total IGAD (Mrd USD)",
                "question": "Quel est le PIB total de la région IGAD en milliards de dollars ?",
                "metric": "pib_total_usd",
            },
            {
                "type": "kpi",
                "title": "Taux de croissance moyen",
                "question": "Quel est le taux de croissance moyen du PIB dans la région IGAD ?",
                "metric": "taux_croissance_moyen",
            },
            {
                "type": "bar",
                "title": "PIB par pays IGAD",
                "question": "Compare le PIB de chaque pays de l'IGAD.",
                "group_by": "pays",
                "metric": "pib_usd",
            },
            {
                "type": "line",
                "title": "Évolution du PIB régional",
                "question": "Montre l'évolution du PIB total IGAD par année.",
                "x": "annee",
                "agg": "year",
            },
        ],
    },
    {
        "template_id": "tmpl-igad-food-security",
        "title": "Sécurité alimentaire IGAD",
        "description": (
            "Tableau de bord IPC (Integrated Food Security Phase Classification) "
            "pour la région IGAD : phases de crise, population en insécurité."
        ),
        "tags": ["igad", "sécurité-alimentaire", "ipc", "fao", "wfp", "crise"],
        "sector": "igad_economic",
        "tiles": [
            {
                "type": "kpi",
                "title": "Phase IPC moyenne",
                "question": "Quelle est la phase IPC moyenne dans la région IGAD ?",
                "metric": "score_securite_alimentaire",
            },
            {
                "type": "bar",
                "title": "Population en crise par pays",
                "question": "Combien de personnes sont en insécurité alimentaire (IPC 3+) par pays ?",
                "group_by": "pays",
                "metric": "population_en_crise",
            },
            {
                "type": "bar",
                "title": "Causes principales par pays",
                "question": "Quelles sont les causes principales de l'insécurité alimentaire par pays ?",
                "group_by": "cause_principale",
            },
        ],
    },
    {
        "template_id": "tmpl-igad-demographics",
        "title": "Démographie IGAD",
        "description": (
            "Indicateurs démographiques de la Corne de l'Afrique : "
            "population totale, urbanisation, espérance de vie, fertilité."
        ),
        "tags": ["igad", "démographie", "population", "afrique-de-l-est"],
        "sector": "igad_economic",
        "tiles": [
            {
                "type": "kpi",
                "title": "Population totale IGAD",
                "question": "Quelle est la population totale de la région IGAD ?",
                "metric": "population_totale",
            },
            {
                "type": "bar",
                "title": "Population par pays",
                "question": "Quelle est la population de chaque pays de l'IGAD ?",
                "group_by": "pays",
            },
            {
                "type": "bar",
                "title": "Taux d'urbanisation par pays",
                "question": "Quel est le taux d'urbanisation dans chaque pays de l'IGAD ?",
                "group_by": "pays",
                "metric": "pop_urbaine_pct",
            },
        ],
    },
]

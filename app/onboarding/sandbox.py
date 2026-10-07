"""Démo sandbox — données synthétiques pré-chargées."""
from __future__ import annotations

import pandas as pd

from app.data.duckdb_store import DataStore

SANDBOX_TABLES: dict[str, pd.DataFrame] = {
    "ventes": pd.DataFrame({
        "date": pd.date_range("2026-01-01", periods=12, freq="MS").astype(str),
        "produit": ["Widget", "Gadget", "Widget", "Gadget", "Widget", "Gadget",
                    "Widget", "Gadget", "Widget", "Gadget", "Widget", "Gadget"],
        "region": ["Nord", "Sud", "Est", "Ouest"] * 3,
        "montant": [12500, 9800, 11200, 8900, 13400, 10200,
                    14100, 11500, 12800, 9600, 15200, 12100],
        "quantite": [125, 98, 112, 89, 134, 102, 141, 115, 128, 96, 152, 121],
    }),
    "clients": pd.DataFrame({
        "client_id": range(1, 11),
        "nom": ["Acme Corp", "BêtaLtd", "GammaInc", "DeltaSA", "EpsilonCo",
                "ZetaGroup", "EtaPlus", "ThetaNet", "IotaFirm", "KappaHolding"],
        "segment": ["PME", "Grand", "PME", "Grand", "PME",
                    "Startup", "PME", "Grand", "Startup", "Grand"],
        "chiffre_affaires": [250000, 1200000, 180000, 950000, 320000,
                             75000, 210000, 880000, 95000, 2100000],
    }),
    "stocks": pd.DataFrame({
        "produit": ["Widget", "Gadget", "Gizmo", "Doohickey", "Thingamajig"],
        "stock_actuel": [450, 230, 87, 312, 56],
        "stock_minimum": [100, 80, 50, 100, 30],
        "prix_unitaire": [99.99, 149.99, 59.99, 79.99, 39.99],
    }),
}


def load_sandbox(store: DataStore) -> list[str]:
    """Load synthetic demo data into the store. Returns list of table names."""
    loaded = []
    for name, df in SANDBOX_TABLES.items():
        store.load_dataframe(name, df)
        loaded.append(name)
    return loaded


def reset_sandbox(store: DataStore) -> list[str]:
    """Clear all tables and reload demo data."""
    store.tables.clear()
    return load_sandbox(store)


def sandbox_questions() -> list[dict]:
    """Example questions demonstrating SovereignBI capabilities."""
    return [
        {"question": "Quel est le total des ventes par produit ?", "table": "ventes"},
        {"question": "Quelle région a le plus de ventes ?", "table": "ventes"},
        {"question": "Quels clients sont dans le segment Grand ?", "table": "clients"},
        {"question": "Quels produits sont en dessous du stock minimum ?", "table": "stocks"},
        {"question": "Quel est le chiffre d'affaires moyen par segment client ?", "table": "clients"},
    ]

"""Connecteur BigQuery lecture seule — charge une table dans un DataFrame."""
from __future__ import annotations

import pandas as pd


def _quote_bq_ident(name: str) -> str:
    if not name or not all(c.isalnum() or c == "_" for c in name):
        raise ValueError(f"Identifiant invalide : {name!r}")
    return f"`{name}`"


def load_bigquery_table(
    table: str,
    dataset: str,
    project: str,
    credentials_path: str | None = None,
    limit: int = 50_000,
) -> pd.DataFrame:
    """Charge project.dataset.table depuis BigQuery en DataFrame (max *limit* lignes)."""
    try:
        from google.cloud import bigquery  # type: ignore[import]
        from google.oauth2 import service_account  # type: ignore[import]
    except ImportError as exc:
        raise ImportError(
            "google-cloud-bigquery requis : pip install google-cloud-bigquery"
        ) from exc

    if credentials_path:
        creds = service_account.Credentials.from_service_account_file(credentials_path)
        client = bigquery.Client(project=project, credentials=creds)
    else:
        client = bigquery.Client(project=project)

    tbl = (
        f"{_quote_bq_ident(project)}.{_quote_bq_ident(dataset)}.{_quote_bq_ident(table)}"
    )
    query = f"SELECT * FROM {tbl} LIMIT {int(limit)}"
    df = client.query(query).to_dataframe()
    return df

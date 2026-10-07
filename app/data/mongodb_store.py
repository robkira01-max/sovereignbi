"""Connecteur MongoDB lecture seule — charge une collection dans un DataFrame."""
from __future__ import annotations

import pandas as pd


def load_mongodb_collection(
    collection: str,
    database: str,
    host: str = "localhost",
    port: int = 27017,
    dsn: str | None = None,
    limit: int = 50_000,
    projection: dict | None = None,
) -> pd.DataFrame:
    """Charge database.collection depuis MongoDB en DataFrame (max *limit* documents)."""
    try:
        from pymongo import MongoClient  # type: ignore[import]
    except ImportError as exc:
        raise ImportError(
            "pymongo requis : pip install pymongo"
        ) from exc

    uri = dsn or f"mongodb://{host}:{port}/"
    client: MongoClient = MongoClient(uri, serverSelectionTimeoutMS=5000)
    try:
        db = client[database]
        coll = db[collection]
        cursor = coll.find(filter={}, projection=projection, limit=limit)
        docs = list(cursor)
        if not docs:
            return pd.DataFrame()
        df = pd.DataFrame(docs)
        if "_id" in df.columns:
            df["_id"] = df["_id"].astype(str)
        return df
    finally:
        client.close()

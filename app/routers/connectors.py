"""Routes de chargement de tables depuis MySQL, SQL Server, Snowflake, BigQuery, MongoDB, Supabase, KNBS, NISR."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.data.mysql_store import load_mysql_table
from app.data.mssql_store import load_mssql_table
from app.data.snowflake_store import load_snowflake_table
from app.data.bigquery_store import load_bigquery_table
from app.data.mongodb_store import load_mongodb_collection
from app.data.supabase_connector import SupabaseConnector
from app.data.knbs_client import KNBSClient
from app.data.nisr_client import NISRClient
from app.security.rbac import RequireRole

router = APIRouter(prefix="/connectors", tags=["connectors"])

_EDITOR = RequireRole("editor")
_VIEWER = RequireRole("viewer")

# Registry in-process : liste des connexions chargées dans cette session
_registry: list[dict] = []


class MySQLRequest(BaseModel):
    table: str
    database: str
    host: str = "localhost"
    port: int = 3306
    dsn: str | None = None


class MSSQLRequest(BaseModel):
    table: str
    database: str
    server: str = "localhost"
    port: int = 1433
    dsn: str | None = None


@router.post("/mysql")
def load_mysql(req: MySQLRequest, request: Request, _: str = Depends(_EDITOR)):
    store = request.app.state.store
    try:
        df = load_mysql_table(
            table=req.table,
            database=req.database,
            host=req.host,
            port=req.port,
            dsn=req.dsn,
        )
    except Exception:
        raise HTTPException(503, "Impossible de se connecter à la base MySQL.")
    table_name = store.load_dataframe(req.table, df)
    _registry.append({"type": "mysql", "table": table_name, "rows": len(df)})
    return {"table": table_name, "rows": len(df)}


@router.post("/mssql")
def load_mssql(req: MSSQLRequest, request: Request, _: str = Depends(_EDITOR)):
    store = request.app.state.store
    try:
        df = load_mssql_table(
            table=req.table,
            database=req.database,
            server=req.server,
            port=req.port,
            dsn=req.dsn,
        )
    except Exception:
        raise HTTPException(503, "Impossible de se connecter à la base SQL Server.")
    table_name = store.load_dataframe(req.table, df)
    _registry.append({"type": "mssql", "table": table_name, "rows": len(df)})
    return {"table": table_name, "rows": len(df)}


class SnowflakeRequest(BaseModel):
    table: str
    database: str
    schema_name: str = "PUBLIC"
    account: str | None = None
    user: str | None = None
    password: str | None = None
    warehouse: str | None = None
    dsn: str | None = None
    limit: int = 50_000


class BigQueryRequest(BaseModel):
    table: str
    dataset: str
    project: str
    credentials_path: str | None = None
    limit: int = 50_000


class MongoDBRequest(BaseModel):
    collection: str
    database: str
    host: str = "localhost"
    port: int = 27017
    dsn: str | None = None
    limit: int = 50_000


@router.post("/snowflake")
def load_snowflake(req: SnowflakeRequest, request: Request, _: str = Depends(_EDITOR)):
    store = request.app.state.store
    try:
        df = load_snowflake_table(
            table=req.table,
            database=req.database,
            schema=req.schema_name,
            account=req.account,
            user=req.user,
            password=req.password,
            warehouse=req.warehouse,
            dsn=req.dsn,
            limit=req.limit,
        )
    except ImportError as e:
        raise HTTPException(501, str(e))
    except Exception:
        raise HTTPException(503, "Impossible de se connecter à Snowflake.")
    table_name = store.load_dataframe(req.table, df)
    _registry.append({"type": "snowflake", "table": table_name, "rows": len(df)})
    return {"table": table_name, "rows": len(df)}


@router.post("/bigquery")
def load_bigquery(req: BigQueryRequest, request: Request, _: str = Depends(_EDITOR)):
    store = request.app.state.store
    try:
        df = load_bigquery_table(
            table=req.table,
            dataset=req.dataset,
            project=req.project,
            credentials_path=req.credentials_path,
            limit=req.limit,
        )
    except ImportError as e:
        raise HTTPException(501, str(e))
    except Exception:
        raise HTTPException(503, "Impossible de se connecter à BigQuery.")
    table_name = store.load_dataframe(req.table, df)
    _registry.append({"type": "bigquery", "table": table_name, "rows": len(df)})
    return {"table": table_name, "rows": len(df)}


@router.post("/mongodb")
def load_mongodb(req: MongoDBRequest, request: Request, _: str = Depends(_EDITOR)):
    store = request.app.state.store
    try:
        df = load_mongodb_collection(
            collection=req.collection,
            database=req.database,
            host=req.host,
            port=req.port,
            dsn=req.dsn,
            limit=req.limit,
        )
    except ImportError as e:
        raise HTTPException(501, str(e))
    except Exception:
        raise HTTPException(503, "Impossible de se connecter à MongoDB.")
    table_name = store.load_dataframe(req.collection, df)
    _registry.append({"type": "mongodb", "table": table_name, "rows": len(df)})
    return {"table": table_name, "rows": len(df)}


class HdxRequest(BaseModel):
    query: str = ""
    dataset_id: str | None = None
    resource_index: int = 0
    table_name: str | None = None


@router.post("/hdx")
def load_hdx(req: HdxRequest, request: Request, _: str = Depends(_EDITOR)):
    """Search HDX for a dataset and load the first CSV resource into DuckDB."""
    from app.data.hdx_client import HdxClient
    store = request.app.state.store
    client = HdxClient()
    try:
        if req.dataset_id:
            url = client.get_resource_url(req.dataset_id, req.resource_index)
        elif req.query:
            results = client.search_datasets(req.query, limit=5)
            if not results:
                raise HTTPException(404, f"Aucun dataset HDX pour : {req.query!r}")
            url = client.get_resource_url(results[0]["name"], req.resource_index)
        else:
            raise HTTPException(422, "Fournir 'query' ou 'dataset_id'.")
        df = client.download_csv(url, strip_hxl=True)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(503, f"Erreur HDX : {exc}") from exc

    table = req.table_name or "hdx_data"
    table_name = store.load_dataframe(table, df)
    _registry.append({"type": "hdx", "table": table_name, "rows": len(df)})
    return {"table": table_name, "rows": len(df), "columns": list(df.columns)}


class SupabaseRequest(BaseModel):
    table: str
    url: str | None = None
    anon_key: str | None = None
    limit: int = 5_000


class SupabaseTablesRequest(BaseModel):
    url: str | None = None
    anon_key: str | None = None


@router.post("/supabase/tables")
def list_supabase_tables(req: SupabaseTablesRequest, _: str = Depends(_EDITOR)):
    """Découvre les tables exposées par un projet Supabase via PostgREST."""
    try:
        client = SupabaseConnector(url=req.url, anon_key=req.anon_key)
        tables = client.list_tables()
    except (EnvironmentError, ValueError) as exc:
        raise HTTPException(422, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, f"Erreur Supabase : {exc}") from exc
    return {"tables": tables}


@router.post("/supabase")
def load_supabase(req: SupabaseRequest, request: Request, _: str = Depends(_EDITOR)):
    """Charge une table Supabase dans DuckDB via PostgREST."""
    store = request.app.state.store
    try:
        client = SupabaseConnector(url=req.url, anon_key=req.anon_key)
        df = client.load_table(req.table, limit=req.limit)
    except (EnvironmentError, ValueError) as exc:
        raise HTTPException(422, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, f"Erreur Supabase : {exc}") from exc
    if df.empty:
        raise HTTPException(404, f"La table {req.table!r} est vide ou introuvable.")
    table_name = store.load_dataframe(req.table, df)
    _registry.append({"type": "supabase", "table": table_name, "rows": len(df), "columns": list(df.columns)})
    return {"table": table_name, "rows": len(df), "columns": list(df.columns)}


# ── KNBS — Kenya National Bureau of Statistics ───────────────────────────────

class KNBSSearchRequest(BaseModel):
    q: str
    rows: int = 20


class KNBSFetchRequest(BaseModel):
    dataset_id: str
    table_name: str | None = None
    max_rows: int = 50_000


@router.post("/knbs/search")
def search_knbs(req: KNBSSearchRequest, _: str = Depends(_VIEWER)):
    """Cherche des datasets KNBS (Kenya Open Data) par mot-clé."""
    try:
        client = KNBSClient()
        datasets = client.search_datasets(req.q, rows=req.rows)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(503, f"KNBS indisponible : {exc}") from exc
    return {
        "results": [
            {
                "id": d.id, "name": d.name, "title": d.title,
                "license_id": d.license_id, "is_permitted": d.is_permitted,
                "resources": len(d.resources),
            }
            for d in datasets
        ]
    }


@router.post("/knbs")
def load_knbs(req: KNBSFetchRequest, request: Request, _: str = Depends(_EDITOR)):
    """Charge le premier CSV d'un dataset KNBS dans DuckDB (après vérification licence)."""
    store = request.app.state.store
    try:
        client = KNBSClient()
        ds, df = client.fetch_dataset_first_csv(req.dataset_id, max_rows=req.max_rows)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(503, f"KNBS indisponible : {exc}") from exc
    if df.empty:
        raise HTTPException(404, f"Dataset KNBS '{req.dataset_id}' vide.")
    tname = req.table_name or ds.name.replace("-", "_")[:64]
    table_name = store.load_dataframe(tname, df)
    _registry.append({
        "type": "knbs", "table": table_name,
        "rows": len(df), "columns": list(df.columns),
        "dataset_id": ds.id, "license_id": ds.license_id,
    })
    return {
        "table": table_name, "rows": len(df),
        "columns": list(df.columns), "license_id": ds.license_id,
    }


# ── NISR — National Institute of Statistics of Rwanda ────────────────────────

class NISRSearchRequest(BaseModel):
    q: str
    rows: int = 20


class NISRFetchRequest(BaseModel):
    dataset_id: str
    table_name: str | None = None
    max_rows: int = 50_000


@router.post("/nisr/search")
def search_nisr(req: NISRSearchRequest, _: str = Depends(_VIEWER)):
    """Cherche des datasets NISR (Rwanda statistics) par mot-clé."""
    try:
        client = NISRClient()
        datasets = client.search_datasets(req.q, rows=req.rows)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(503, f"NISR indisponible : {exc}") from exc
    return {
        "results": [
            {
                "id": d.id, "name": d.name, "title": d.title,
                "license_id": d.license_id, "is_permitted": d.is_permitted,
                "resources": len(d.resources),
            }
            for d in datasets
        ]
    }


@router.post("/nisr")
def load_nisr(req: NISRFetchRequest, request: Request, _: str = Depends(_EDITOR)):
    """Charge le premier CSV d'un dataset NISR dans DuckDB (après vérification licence)."""
    store = request.app.state.store
    try:
        client = NISRClient()
        ds, df = client.fetch_dataset_first_csv(req.dataset_id, max_rows=req.max_rows)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(503, f"NISR indisponible : {exc}") from exc
    if df.empty:
        raise HTTPException(404, f"Dataset NISR '{req.dataset_id}' vide.")
    tname = req.table_name or ds.name.replace("-", "_")[:64]
    table_name = store.load_dataframe(tname, df)
    _registry.append({
        "type": "nisr", "table": table_name,
        "rows": len(df), "columns": list(df.columns),
        "dataset_id": ds.id, "license_id": ds.license_id,
    })
    return {
        "table": table_name, "rows": len(df),
        "columns": list(df.columns), "license_id": ds.license_id,
    }


@router.get("")
def list_connectors(_: str = Depends(_VIEWER)):
    return {"connectors": _registry}

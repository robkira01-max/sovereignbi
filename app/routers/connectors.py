"""Routes de chargement de tables depuis MySQL, SQL Server, Snowflake, BigQuery, MongoDB."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.data.mysql_store import load_mysql_table
from app.data.mssql_store import load_mssql_table
from app.data.snowflake_store import load_snowflake_table
from app.data.bigquery_store import load_bigquery_table
from app.data.mongodb_store import load_mongodb_collection
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


@router.get("")
def list_connectors(_: str = Depends(_VIEWER)):
    return {"connectors": _registry}

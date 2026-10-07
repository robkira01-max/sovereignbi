"""Routes de chargement de tables depuis MySQL et SQL Server."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.data.mysql_store import load_mysql_table
from app.data.mssql_store import load_mssql_table
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


@router.get("")
def list_connectors(_: str = Depends(_VIEWER)):
    return {"connectors": _registry}

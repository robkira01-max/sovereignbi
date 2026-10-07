import tempfile
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.api.middleware import ApiVersionMiddleware
from app.api.v1.router import router as v1_router
from app.cache.query_cache import QueryCache
from app.data.duckdb_store import DataStore
from app.llm.ollama_client import OllamaClient
from app.pipeline.graph import build_graph, load_semantic
from app.rag.doc_store import DocStore
from app.multitenancy.org import OrgRegistry
from app.routers.admin import router as admin_router
from app.routers.connectors import router as connectors_router
from app.routers.dashboards import router as dashboards_router
from app.routers.docs_rag import router as docs_router
from app.routers.embed import router as embed_router
from app.routers.export import router as export_router
from app.routers.alerts import router as alerts_router
from app.routers.compliance import router as compliance_router
from app.routers.marketplace import router as marketplace_router
from app.routers.onboarding import router as onboarding_router
from app.routers.orgs import router as orgs_router
from app.routers.wizard import router as wizard_router
from app.security.rbac import RequireRole

app = FastAPI(
    title="SovereignBI",
    version="1.0.0",
    description=(
        "Outil BI conversationnel 100% local — text-to-SQL, LLM via Ollama, DuckDB. "
        "Aucune donnée ne quitte votre infrastructure."
    ),
    openapi_tags=[
        {"name": "v1", "description": "API REST versionnée — endpoints stables"},
        {"name": "alerts", "description": "Règles d'alerte et surveillance SQL"},
        {"name": "export", "description": "Export Excel et PDF"},
        {"name": "dashboards", "description": "Tableaux de bord persistants"},
        {"name": "orgs", "description": "Multi-tenant — gestion des organisations"},
        {"name": "cache", "description": "Statistiques et invalidation du cache requêtes"},
    ],
)
app.add_middleware(ApiVersionMiddleware)
app.include_router(v1_router)
app.include_router(admin_router)
app.include_router(dashboards_router)
app.include_router(export_router)
app.include_router(connectors_router)
app.include_router(docs_router)
app.include_router(wizard_router)
app.include_router(embed_router)
app.include_router(alerts_router)
app.include_router(compliance_router)
app.include_router(marketplace_router)
app.include_router(onboarding_router)
app.include_router(orgs_router)

store = DataStore()
doc_store = DocStore()
org_registry = OrgRegistry()
query_cache = QueryCache()
_graph = None

app.state.store = store
app.state.doc_store = doc_store
app.state.org_registry = org_registry
app.state.query_cache = query_cache


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph(OllamaClient(), store, load_semantic(), doc_store=doc_store)
    return _graph


app.state.get_graph = get_graph

_VIEWER = RequireRole("viewer")
_EDITOR = RequireRole("editor")
_ADMIN = RequireRole("admin")


class AskRequest(BaseModel):
    question: str
    dry_run: bool = False
    use_cache: bool = True


@app.get("/health")
def health():
    return {"status": "ok", "tables": sorted(store.tables)}


@app.post("/upload")
async def upload(file: UploadFile = File(...), _: str = Depends(_VIEWER)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".csv", ".xlsx", ".xlsm"}:
        raise HTTPException(400, "Formats acceptés : CSV, XLSX, XLSM")
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / Path(file.filename).name
        p.write_bytes(await file.read())
        tables = store.load_file(p)
    query_cache.invalidate()
    return {"tables": tables}


@app.post("/ask")
def ask(req: AskRequest, _: str = Depends(_VIEWER)):
    if not store.tables:
        raise HTTPException(400, "Aucune donnée chargée. Utilisez /upload d'abord.")

    table_names = frozenset(store.tables)
    if req.use_cache and not req.dry_run:
        cached = query_cache.get(req.question, table_names)
        if cached is not None:
            return {**cached, "cached": True}

    s = get_graph().invoke({"question": req.question, "dry_run": req.dry_run})
    result = {
        "sql": s.get("sql"),
        "columns": s.get("columns", []),
        "rows": s.get("rows", [])[:200],
        "answer": s.get("answer"),
        "error": s.get("error"),
        "attempts": s.get("attempts"),
        "confidence": s.get("confidence"),
        "cached": False,
    }
    if req.use_cache and not req.dry_run and not s.get("error"):
        query_cache.set(req.question, table_names, result)
    return result


@app.get("/cache/stats", tags=["cache"])
def cache_stats(_: str = Depends(_VIEWER)):
    return query_cache.stats()


@app.delete("/cache", tags=["cache"])
def invalidate_cache(_: str = Depends(_ADMIN)):
    count = query_cache.invalidate()
    return {"invalidated": count}


# Serve React build if dist/ exists (optional — not required for API usage)
_REACT_DIST = Path(__file__).parent.parent / "frontend" / "dist"
if _REACT_DIST.exists():
    from fastapi.staticfiles import StaticFiles
    app.mount("/app", StaticFiles(directory=str(_REACT_DIST), html=True), name="frontend")

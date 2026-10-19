import os
import tempfile
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from app.api.middleware import (
    ApiVersionMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
)
from app.api.v1.router import router as v1_router
from app.startup import log_startup_warnings, validate_env
from app.cache.query_cache import QueryCache
from app.cache.persistent_cache import PersistentQueryCache
from app.data.duckdb_store import DataStore
from app.llm import get_llm_client
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
from app.routers.accuracy import router as accuracy_router
from app.routers.compliance import router as compliance_router
from app.routers.marketplace import router as marketplace_router
from app.routers.onboarding import router as onboarding_router
from app.routers.orgs import router as orgs_router
from app.routers.wizard import router as wizard_router
from app.routers.template_import import router as template_import_router
from app.routers.addin import router as addin_router
from app.routers.sync import router as sync_router
from app.routers.semantic import router as semantic_router
from app.routers.chatbot import router as chatbot_router
from app.sync.scheduler import CronScheduler
from app.monitoring.metrics import (
    active_tables,
    ask_duration_seconds,
    asks_total,
    cache_hits_total,
    cache_misses_total,
    render_all,
    uploads_total,
)
from app.security.rbac import RequireRole
from app.security.audit import audit_configuration, log_audit_results


@asynccontextmanager
async def lifespan(app: FastAPI):
    warnings = validate_env()
    log_startup_warnings(warnings)
    findings = audit_configuration()
    log_audit_results(findings)
    scheduler = CronScheduler()
    scheduler.start()
    app.state.scheduler = scheduler
    yield
    scheduler.stop()


def _cors_origins() -> list[str]:
    raw = os.environ.get(
        "SOVEREIGN_CORS_ORIGINS",
        "http://localhost:8000,http://localhost:9000,"
        "https://excel.officeapps.live.com,https://officeapps.live.com",
    )
    return [o.strip() for o in raw.split(",") if o.strip()]


app = FastAPI(
    title="SovereignBI",
    version="1.0.0",
    description=(
        "Outil BI conversationnel souverain — text-to-SQL, LLM local ou API, DuckDB. "
        "Aucune donnée ne quitte votre infrastructure sans votre accord."
    ),
    openapi_tags=[
        {"name": "v1", "description": "API REST versionnée — endpoints stables"},
        {"name": "alerts", "description": "Règles d'alerte et surveillance SQL"},
        {"name": "export", "description": "Export Excel et PDF"},
        {"name": "dashboards", "description": "Tableaux de bord persistants"},
        {"name": "orgs", "description": "Multi-tenant — gestion des organisations"},
        {"name": "cache", "description": "Statistiques et invalidation du cache requêtes"},
    ],
    lifespan=lifespan,
)

# Middleware stack (applied in reverse order — last added = outermost)
app.add_middleware(ApiVersionMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["X-Api-Key", "Content-Type", "Accept"],
)
app.include_router(v1_router)
app.include_router(admin_router)
app.include_router(dashboards_router)
app.include_router(export_router)
app.include_router(connectors_router)
app.include_router(docs_router)
app.include_router(wizard_router)
app.include_router(embed_router)
app.include_router(alerts_router)
app.include_router(accuracy_router)
app.include_router(compliance_router)
app.include_router(marketplace_router)
app.include_router(onboarding_router)
app.include_router(orgs_router)
app.include_router(template_import_router)
app.include_router(addin_router)
app.include_router(sync_router)
app.include_router(semantic_router)
app.include_router(chatbot_router)

store = DataStore()
doc_store = DocStore()
org_registry = OrgRegistry()
_sqlite_path = os.environ.get("CACHE_SQLITE_PATH", "")
query_cache: QueryCache = (
    PersistentQueryCache() if _sqlite_path else QueryCache()
)
_graph = None

app.state.store = store
app.state.doc_store = doc_store
app.state.org_registry = org_registry
app.state.query_cache = query_cache


def get_graph():
    global _graph
    if _graph is None:
        active_text = getattr(app.state, "active_semantic_text", None)
        if active_text:
            from app.semantic.model import SemanticModel
            sem = SemanticModel(schema_version="2")
            sem._raw_text = active_text  # passed through if pipeline supports it
        else:
            sem = load_semantic()
        _graph = build_graph(get_llm_client(), store, sem, doc_store=doc_store)
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
    uploads_total.inc()
    active_tables.set(len(store.tables))
    return {"tables": tables}


@app.post("/ask")
def ask(req: AskRequest, _: str = Depends(_VIEWER)):
    if not store.tables:
        raise HTTPException(400, "Aucune donnée chargée. Utilisez /upload d'abord.")

    table_names = frozenset(store.tables)
    if req.use_cache and not req.dry_run:
        cached = query_cache.get(req.question, table_names)
        if cached is not None:
            cache_hits_total.inc()
            return {**cached, "cached": True}

    cache_misses_total.inc()
    t0 = time.perf_counter()
    s = get_graph().invoke({"question": req.question, "dry_run": req.dry_run})
    ask_duration_seconds.observe(time.perf_counter() - t0)
    status = "error" if s.get("error") else "success"
    asks_total.inc(status=status)

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


@app.get("/metrics", tags=["monitoring"], response_class=PlainTextResponse)
def prometheus_metrics():
    """Métriques Prometheus au format text/plain exposition."""
    active_tables.set(len(store.tables))
    return PlainTextResponse(render_all(), media_type="text/plain; version=0.0.4; charset=utf-8")


@app.get("/ready", tags=["monitoring"])
def readiness():
    """Kubernetes readiness probe."""
    return {"ready": True, "tables": len(store.tables)}


@app.get("/live", tags=["monitoring"])
def liveness():
    """Kubernetes liveness probe."""
    return {"alive": True}


# Serve Excel add-in static files
_ADDIN_DIR = Path(__file__).parent.parent / "frontend" / "excel-addin"
if _ADDIN_DIR.exists():
    from fastapi.staticfiles import StaticFiles as _StaticFiles
    app.mount("/addin/excel", _StaticFiles(directory=str(_ADDIN_DIR)), name="excel-addin")

# Serve React build if dist/ exists (optional — not required for API usage)
_REACT_DIST = Path(__file__).parent.parent / "frontend" / "dist"
if _REACT_DIST.exists():
    from fastapi.responses import RedirectResponse
    from fastapi.staticfiles import StaticFiles

    @app.get("/", include_in_schema=False)
    def root_redirect():
        return RedirectResponse(url="/app/")

    app.mount("/app", StaticFiles(directory=str(_REACT_DIST), html=True), name="frontend")

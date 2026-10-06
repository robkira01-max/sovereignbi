import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.data.duckdb_store import DataStore
from app.llm.ollama_client import OllamaClient
from app.pipeline.graph import build_graph, load_semantic
from app.routers.admin import router as admin_router
from app.routers.dashboards import router as dashboards_router

app = FastAPI(title="SovereignBI", version="0.1.0")
app.include_router(admin_router)
app.include_router(dashboards_router)
store = DataStore()
_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph(OllamaClient(), store, load_semantic())
    return _graph


class AskRequest(BaseModel):
    question: str
    dry_run: bool = False


@app.get("/health")
def health():
    return {"status": "ok", "tables": sorted(store.tables)}


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".csv", ".xlsx", ".xlsm"}:
        raise HTTPException(400, "Formats acceptés : CSV, XLSX, XLSM")
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / Path(file.filename).name
        p.write_bytes(await file.read())
        tables = store.load_file(p)
    return {"tables": tables}


@app.post("/ask")
def ask(req: AskRequest):
    if not store.tables:
        raise HTTPException(400, "Aucune donnée chargée. Utilisez /upload d'abord.")
    s = get_graph().invoke({"question": req.question, "dry_run": req.dry_run})
    return {
        "sql": s.get("sql"),
        "columns": s.get("columns", []),
        "rows": s.get("rows", [])[:200],
        "answer": s.get("answer"),
        "error": s.get("error"),
        "attempts": s.get("attempts"),
    }

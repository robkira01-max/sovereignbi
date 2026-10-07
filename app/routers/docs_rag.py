"""Routes RAG documentaire : ingestion PDF/DOCX et recherche de chunks."""
from __future__ import annotations

import io
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import JSONResponse

from app.rag.doc_pipeline import ingest_document
from app.security.rbac import RequireRole

router = APIRouter(prefix="/documents", tags=["documents"])

_EDITOR = RequireRole("editor")
_VIEWER = RequireRole("viewer")

_MAX_BYTES = 50 * 1024 * 1024  # 50 MB
_ALLOWED_EXT = {".pdf", ".docx"}


@router.post("/ingest")
async def ingest_doc(
    request: Request,
    file: UploadFile = File(...),
    load_tables: bool = Query(default=False),
    _: str = Depends(_EDITOR),
):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in _ALLOWED_EXT:
        raise HTTPException(400, f"Extension non supportée. Acceptés : {', '.join(_ALLOWED_EXT)}")

    content = await file.read()
    if len(content) > _MAX_BYTES:
        raise HTTPException(413, "Fichier trop volumineux (max 50 MB).")

    doc_store = request.app.state.doc_store
    data_store = getattr(request.app.state, "store", None) if load_tables else None

    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)
        result = ingest_document(tmp_path, doc_store, data_store)
        tmp_path.unlink(missing_ok=True)
    except Exception as exc:
        raise HTTPException(422, f"Erreur d'ingestion : {exc}")

    return {
        "doc_id": result.doc_id,
        "chunks": result.text_chunks,
        "source": file.filename,
        "tables_found": result.tables_found,
        "tables_loaded": result.tables_loaded,
    }


@router.get("/search")
def search_docs(
    q: str,
    k: int = 5,
    request: Request = None,
    _: str = Depends(_VIEWER),
):
    doc_store = request.app.state.doc_store
    chunks = doc_store.search(q, k=min(k, 20))
    return {
        "results": [
            {"source": c.source, "page": c.page, "text": c.text, "score": 1.0}
            for c in chunks
        ]
    }


@router.get("")
def list_docs(request: Request, _: str = Depends(_VIEWER)):
    doc_store = request.app.state.doc_store
    return {"documents": doc_store.list_docs()}


@router.delete("/{doc_id}")
def delete_doc(doc_id: str, request: Request, _: str = Depends(_EDITOR)):
    doc_store = request.app.state.doc_store
    n = doc_store.clear(doc_id)
    if n == 0:
        raise HTTPException(404, "Document introuvable.")
    return {"deleted_chunks": n}

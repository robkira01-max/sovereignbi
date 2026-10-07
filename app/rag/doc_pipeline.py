"""Pipeline complet d'ingestion documentaire : texte + tableaux."""
from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from app.rag.table_extractor import extract_tables_from_docx, extract_tables_from_pdf

logger = logging.getLogger(__name__)


@dataclass
class IngestResult:
    doc_id: str
    source: str
    text_chunks: int
    tables_found: int
    tables_loaded: int
    errors: list[str] = field(default_factory=list)


def _safe_table_name(source_stem: str, page: int, idx: int) -> str:
    name = re.sub(r"\W+", "_", source_stem.lower()).strip("_")
    name = f"{name}_p{page}_t{idx}"
    if not name or name[0].isdigit():
        name = f"t_{name}"
    return name[:64]


def ingest_document(
    path: str | Path,
    doc_store,
    data_store=None,
) -> IngestResult:
    """Full ingestion pipeline: text chunks + table extraction.

    If data_store is provided, tables with confidence > 0.5 are loaded as DuckDB tables.
    """
    p = Path(path)
    content = p.read_bytes()
    doc_id = hashlib.sha256(content).hexdigest()
    errors: list[str] = []

    # 1. Text chunks
    try:
        text_chunks = doc_store.ingest(p)
    except Exception as exc:
        errors.append(f"text extraction: {exc}")
        text_chunks = 0

    # 2. Table extraction
    tables: list = []
    try:
        ext = p.suffix.lower()
        if ext == ".pdf":
            tables = extract_tables_from_pdf(p)
        elif ext == ".docx":
            tables = extract_tables_from_docx(p)
    except Exception as exc:
        errors.append(f"table extraction: {exc}")

    tables_found = len(tables)
    tables_loaded = 0

    # 3. Load high-confidence tables into DataStore
    if data_store is not None:
        for t in tables:
            if t.confidence <= 0.5:
                continue
            tname = _safe_table_name(p.stem, t.page, t.table_index)
            try:
                data_store.load_dataframe(tname, t.df)
                tables_loaded += 1
            except Exception as exc:
                errors.append(f"load table {tname}: {exc}")
                logger.warning("Failed to load table %s: %s", tname, exc)

    return IngestResult(
        doc_id=doc_id,
        source=p.name,
        text_chunks=text_chunks,
        tables_found=tables_found,
        tables_loaded=tables_loaded,
        errors=errors,
    )

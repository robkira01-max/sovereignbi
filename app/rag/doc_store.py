"""Indexation de documents PDF/DOCX dans DuckDB pour injection en contexte."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import duckdb


@dataclass
class DocChunk:
    doc_id: str
    source: str
    page: int
    chunk_index: int
    text: str


_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS doc_chunks (
    doc_id VARCHAR,
    source VARCHAR,
    page INTEGER,
    chunk_index INTEGER,
    text VARCHAR
)
"""


def _chunk_text(text: str, max_len: int = 500, overlap: int = 50) -> list[str]:
    """Split text into chunks of max_len chars with overlap, breaking on spaces."""
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    length = len(text)
    while start < length:
        end = start + max_len
        if end >= length:
            chunk = text[start:]
        else:
            # walk back to a space
            space = text.rfind(" ", start, end)
            end = space if space > start else end
            chunk = text[start:end]
        chunk = chunk.strip()
        if chunk:
            chunks.append(chunk)
        if end >= length:
            break
        start = end - overlap
        if start <= 0:
            start = end
    return chunks


class DocStore:
    """Index de chunks documentaires dans DuckDB avec recherche ILIKE."""

    def __init__(self, con: duckdb.DuckDBPyConnection | None = None):
        self._con = con or duckdb.connect(":memory:")
        self._con.execute(_CREATE_TABLE)

    def ingest(self, path: str | Path, use_ocr_fallback: bool = True) -> int:
        p = Path(path)
        content = p.read_bytes()
        doc_id = hashlib.sha256(content).hexdigest()

        # deduplicate
        existing = self._con.execute(
            "SELECT COUNT(*) FROM doc_chunks WHERE doc_id = ?", [doc_id]
        ).fetchone()[0]
        if existing:
            return 0

        ext = p.suffix.lower()
        if ext == ".pdf":
            if use_ocr_fallback:
                from app.rag.ocr import extract_text_with_fallback
                pages = extract_text_with_fallback(p)
            else:
                pages = _extract_pdf(content)
        elif ext == ".docx":
            pages = _extract_docx(content)
        else:
            raise ValueError(f"Extension non supportée : {ext!r}")

        count = 0
        for page_num, text in enumerate(pages, start=1):
            for chunk_idx, chunk in enumerate(_chunk_text(text)):
                self._con.execute(
                    "INSERT INTO doc_chunks VALUES (?, ?, ?, ?, ?)",
                    [doc_id, p.name, page_num, chunk_idx, chunk],
                )
                count += 1
        return count

    def ingest_bytes(self, content: bytes, filename: str) -> int:
        """Ingère du contenu binaire (pour tests et routes HTTP)."""
        import io

        doc_id = hashlib.sha256(content).hexdigest()
        existing = self._con.execute(
            "SELECT COUNT(*) FROM doc_chunks WHERE doc_id = ?", [doc_id]
        ).fetchone()[0]
        if existing:
            return 0

        ext = Path(filename).suffix.lower()
        if ext == ".pdf":
            pages = _extract_pdf(content)
        elif ext == ".docx":
            pages = _extract_docx(content)
        else:
            raise ValueError(f"Extension non supportée : {ext!r}")

        count = 0
        for page_num, text in enumerate(pages, start=1):
            for chunk_idx, chunk in enumerate(_chunk_text(text)):
                self._con.execute(
                    "INSERT INTO doc_chunks VALUES (?, ?, ?, ?, ?)",
                    [doc_id, filename, page_num, chunk_idx, chunk],
                )
                count += 1
        return count

    def search(self, query: str, k: int = 5) -> list[DocChunk]:
        terms = [t.strip() for t in query.split() if len(t.strip()) > 2]
        if not terms:
            rows = self._con.execute(
                "SELECT doc_id, source, page, chunk_index, text FROM doc_chunks LIMIT ?",
                [k],
            ).fetchall()
        else:
            conditions = " OR ".join(["text ILIKE ?" for _ in terms])
            params = [f"%{t}%" for t in terms] + [k]
            rows = self._con.execute(
                f"SELECT doc_id, source, page, chunk_index, text "
                f"FROM doc_chunks WHERE {conditions} LIMIT ?",
                params,
            ).fetchall()
        return [DocChunk(*r) for r in rows]

    def format_context(self, chunks: list[DocChunk]) -> str:
        if not chunks:
            return ""
        lines = ["Contexte documentaire :"]
        for c in chunks:
            lines.append(f"[{c.source}, p.{c.page}] {c.text}")
        return "\n".join(lines)

    def clear(self, doc_id: str | None = None) -> int:
        if doc_id:
            n = self._con.execute(
                "SELECT COUNT(*) FROM doc_chunks WHERE doc_id = ?", [doc_id]
            ).fetchone()[0]
            self._con.execute("DELETE FROM doc_chunks WHERE doc_id = ?", [doc_id])
        else:
            n = self._con.execute("SELECT COUNT(*) FROM doc_chunks").fetchone()[0]
            self._con.execute("DELETE FROM doc_chunks")
        return n

    @property
    def doc_count(self) -> int:
        return self._con.execute(
            "SELECT COUNT(DISTINCT doc_id) FROM doc_chunks"
        ).fetchone()[0]

    @property
    def chunk_count(self) -> int:
        return self._con.execute("SELECT COUNT(*) FROM doc_chunks").fetchone()[0]

    def list_docs(self) -> list[dict]:
        rows = self._con.execute(
            "SELECT doc_id, source, COUNT(*) as chunk_count "
            "FROM doc_chunks GROUP BY doc_id, source"
        ).fetchall()
        return [{"doc_id": r[0], "source": r[1], "chunk_count": r[2]} for r in rows]


def _extract_pdf(content: bytes) -> list[str]:
    import io
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(content))
    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text)
    return pages


def _extract_docx(content: bytes) -> list[str]:
    import io
    import docx

    doc = docx.Document(io.BytesIO(content))
    # group paragraphs into synthetic "pages" of ~2000 chars each
    pages: list[str] = []
    current: list[str] = []
    current_len = 0
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        current.append(text)
        current_len += len(text)
        if current_len >= 2000:
            pages.append("\n".join(current))
            current = []
            current_len = 0
    if current:
        pages.append("\n".join(current))
    return pages or [""]

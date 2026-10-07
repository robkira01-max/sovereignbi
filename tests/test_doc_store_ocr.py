"""Tests for DocStore.ingest OCR integration."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock
import io

import pytest

from app.rag.doc_store import DocStore


def _minimal_pdf() -> bytes:
    """Minimal valid-ish PDF bytes for testing."""
    return b"%PDF-1.4 fake content"


def test_ingest_with_ocr_fallback_false_uses_extract_pdf(tmp_path):
    """use_ocr_fallback=False should call _extract_pdf (pypdf direct)."""
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(_minimal_pdf())

    store = DocStore()
    with patch("app.rag.doc_store._extract_pdf", return_value=["Page text content here."]) as mock_extract:
        store.ingest(pdf, use_ocr_fallback=False)
    mock_extract.assert_called_once()


def test_ingest_with_ocr_fallback_true_uses_extract_with_fallback(tmp_path):
    """use_ocr_fallback=True should call extract_text_with_fallback from ocr module."""
    pdf = tmp_path / "scanned.pdf"
    pdf.write_bytes(_minimal_pdf())

    store = DocStore()
    import app.rag.ocr as ocr_mod
    with patch.object(ocr_mod, "extract_text_with_fallback", return_value=["OCR extracted text that is long enough."]):
        store.ingest(pdf, use_ocr_fallback=True)
    # Verify chunks were created from the returned text
    assert store.chunk_count >= 1


def test_ingest_ocr_fallback_default_is_true(tmp_path):
    """Default use_ocr_fallback=True."""
    import inspect
    from app.rag.doc_store import DocStore
    sig = inspect.signature(DocStore.ingest)
    assert sig.parameters["use_ocr_fallback"].default is True


def test_ingest_doc_route_returns_tables_fields(tmp_path):
    """Route /documents/ingest response includes tables_found and tables_loaded."""
    import os
    os.environ.setdefault("SOVEREIGN_EDITOR_KEY", "test-editor-key-s6")

    from fastapi.testclient import TestClient
    import app.main as m

    client = TestClient(m.app)

    from app.rag.doc_pipeline import IngestResult
    fake_result = IngestResult(
        doc_id="abc123",
        source="test.pdf",
        text_chunks=5,
        tables_found=2,
        tables_loaded=1,
    )

    with patch("app.routers.docs_rag.ingest_document", return_value=fake_result):
        pdf_bytes = b"%PDF-1.4 fake"
        resp = client.post(
            "/documents/ingest",
            files={"file": ("test.pdf", pdf_bytes, "application/pdf")},
            headers={"X-Api-Key": "test-editor-key-s6"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["tables_found"] == 2
    assert data["tables_loaded"] == 1
    assert data["chunks"] == 5

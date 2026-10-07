"""Tests des routes /docs (RAG documentaire)."""
from __future__ import annotations

import hashlib
import io
import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

_EDITOR_KEY = os.environ.get("SOVEREIGN_EDITOR_KEY", "test-editor-key-s6")
_VIEWER_KEY = os.environ.get("SOVEREIGN_VIEWER_KEY", "test-viewer-key-s6")
_E = {"X-Api-Key": _EDITOR_KEY}
_V = {"X-Api-Key": _VIEWER_KEY}

_FAKE_PDF = b"%PDF-1.4 fake pdf content for testing purposes"
_FAKE_DOCX = b"PK fake docx content"


@pytest.fixture
def client():
    import app.main as m
    from app.rag.doc_store import DocStore

    # Fresh doc_store per test
    ds = DocStore()
    original = m.app.state.doc_store
    m.app.state.doc_store = ds
    yield TestClient(m.app)
    m.app.state.doc_store = original


def test_ingest_pdf_requires_editor_role(client):
    r = client.post(
        "/documents/ingest",
        files={"file": ("doc.pdf", _FAKE_PDF, "application/pdf")},
        headers=_V,
    )
    assert r.status_code == 403


def test_ingest_accepts_pdf(client):
    with patch("app.rag.ocr.extract_text_with_fallback", return_value=["texte du rapport"]):
        r = client.post(
            "/documents/ingest",
            files={"file": ("rapport.pdf", _FAKE_PDF, "application/pdf")},
            headers=_E,
        )
    assert r.status_code == 200
    data = r.json()
    assert data["source"] == "rapport.pdf"
    assert data["chunks"] >= 1
    assert len(data["doc_id"]) == 64  # sha256 hex


def test_ingest_accepts_docx(client):
    with patch("app.rag.doc_store._extract_docx", return_value=["analyse financière"]):
        r = client.post(
            "/documents/ingest",
            files={"file": ("analyse.docx", _FAKE_DOCX, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            headers=_E,
        )
    assert r.status_code == 200


def test_ingest_rejects_unsupported_extension(client):
    r = client.post(
        "/documents/ingest",
        files={"file": ("data.csv", b"a,b\n1,2", "text/csv")},
        headers=_E,
    )
    assert r.status_code == 400


def test_ingest_rejects_large_file(client):
    large = b"x" * (51 * 1024 * 1024)
    r = client.post(
        "/documents/ingest",
        files={"file": ("big.pdf", large, "application/pdf")},
        headers=_E,
    )
    assert r.status_code == 413


def test_search_docs_requires_viewer_role(client):
    r = client.get("/documents/search?q=test")
    assert r.status_code == 401


def test_search_docs_returns_results(client):
    with patch("app.rag.ocr.extract_text_with_fallback", return_value=["Ontario ventes rapport"]):
        client.post(
            "/documents/ingest",
            files={"file": ("r.pdf", _FAKE_PDF, "application/pdf")},
            headers=_E,
        )
    r = client.get("/documents/search?q=Ontario", headers=_V)
    assert r.status_code == 200
    results = r.json()["results"]
    assert len(results) >= 1


def test_list_docs_requires_auth(client):
    r = client.get("/documents")
    assert r.status_code == 401


def test_list_docs_with_viewer(client):
    r = client.get("/documents", headers=_V)
    assert r.status_code == 200
    assert "documents" in r.json()


def test_delete_doc(client):
    with patch("app.rag.ocr.extract_text_with_fallback", return_value=["texte à supprimer"]):
        resp = client.post(
            "/documents/ingest",
            files={"file": ("del.pdf", _FAKE_PDF, "application/pdf")},
            headers=_E,
        )
    doc_id = resp.json()["doc_id"]
    r = client.delete(f"/documents/{doc_id}", headers=_E)
    assert r.status_code == 200
    assert r.json()["deleted_chunks"] >= 1

"""Tests du DocStore — PDF/DOCX mockés, aucun fichier réel."""
from __future__ import annotations

import hashlib
from unittest.mock import MagicMock, patch

import pytest

from app.rag.doc_store import DocStore, _chunk_text


# ── chunk_text ──────────────────────────────────────────────────────────────

def test_chunk_text_empty_returns_empty():
    assert _chunk_text("") == []


def test_chunk_text_short_text_returns_one_chunk():
    result = _chunk_text("Hello world", max_len=500)
    assert result == ["Hello world"]


def test_chunk_text_splits_on_word_boundary():
    text = "A " * 300  # 600 chars
    chunks = _chunk_text(text, max_len=500)
    assert len(chunks) >= 2
    for c in chunks:
        assert len(c) <= 500


def test_chunk_text_overlap():
    text = "word " * 200
    chunks = _chunk_text(text, max_len=100, overlap=20)
    assert len(chunks) >= 2


def test_chunk_text_no_empty_chunks():
    text = "   word   " * 100
    for c in _chunk_text(text):
        assert c.strip() != ""


# ── DocStore basic ───────────────────────────────────────────────────────────

def _make_store():
    return DocStore()


def _fake_pdf_content(text: str) -> bytes:
    return f"%PDF-1.4 fake {text}".encode()


def _fake_docx_content(text: str) -> bytes:
    return b"PK fake docx " + text.encode()


# ── ingest PDF ───────────────────────────────────────────────────────────────

def test_ingest_pdf_creates_chunks():
    ds = _make_store()
    content = _fake_pdf_content("rapport trimestriel ventes Ontario")
    with patch("app.rag.doc_store._extract_pdf", return_value=["rapport trimestriel " * 30]):
        n = ds.ingest_bytes(content, "rapport.pdf")
    assert n > 0
    assert ds.chunk_count == n


def test_ingest_docx_creates_chunks():
    ds = _make_store()
    content = _fake_docx_content("analyse financière")
    with patch("app.rag.doc_store._extract_docx", return_value=["analyse financière " * 30]):
        n = ds.ingest_bytes(content, "analyse.docx")
    assert n > 0


def test_ingest_deduplicates_same_doc():
    ds = _make_store()
    content = _fake_pdf_content("texte identique")
    with patch("app.rag.doc_store._extract_pdf", return_value=["texte identique " * 20]):
        n1 = ds.ingest_bytes(content, "doc.pdf")
        n2 = ds.ingest_bytes(content, "doc.pdf")
    assert n1 > 0
    assert n2 == 0
    assert ds.chunk_count == n1


def test_ingest_rejects_unknown_extension():
    ds = _make_store()
    with pytest.raises(ValueError, match="Extension"):
        ds.ingest_bytes(b"data", "fichier.txt")


# ── search ───────────────────────────────────────────────────────────────────

def test_search_returns_relevant_chunks():
    ds = _make_store()
    content = b"some content"
    with patch("app.rag.doc_store._extract_pdf", return_value=["ventes Ontario région important"]):
        ds.ingest_bytes(content, "doc.pdf")
    results = ds.search("Ontario")
    assert len(results) >= 1
    assert any("Ontario" in r.text for r in results)


def test_search_empty_store_returns_empty():
    ds = _make_store()
    assert ds.search("quelque chose") == []


def test_search_respects_k():
    ds = _make_store()
    text = "mot clé " * 10
    contents = [f"doc{i}".encode() for i in range(10)]
    for i, c in enumerate(contents):
        with patch("app.rag.doc_store._extract_pdf", return_value=[text]):
            ds.ingest_bytes(c, f"doc{i}.pdf")
    results = ds.search("mot", k=3)
    assert len(results) <= 3


# ── format_context ───────────────────────────────────────────────────────────

def test_format_context_includes_source_and_page():
    ds = _make_store()
    with patch("app.rag.doc_store._extract_pdf", return_value=["texte important du rapport"]):
        ds.ingest_bytes(b"pdf_content", "rapport.pdf")
    chunks = ds.search("texte")
    ctx = ds.format_context(chunks)
    assert "rapport.pdf" in ctx
    assert "texte" in ctx.lower()


def test_format_context_empty_returns_empty():
    ds = _make_store()
    assert ds.format_context([]) == ""


# ── clear ────────────────────────────────────────────────────────────────────

def test_clear_removes_all_chunks():
    ds = _make_store()
    with patch("app.rag.doc_store._extract_pdf", return_value=["contenu du document"]):
        ds.ingest_bytes(b"a", "a.pdf")
        ds.ingest_bytes(b"b", "b.pdf")
    assert ds.chunk_count > 0
    n = ds.clear()
    assert n > 0
    assert ds.chunk_count == 0


def test_clear_by_doc_id_removes_only_that_doc():
    ds = _make_store()
    content_a = b"content_a_unique"
    content_b = b"content_b_unique"
    doc_id_a = hashlib.sha256(content_a).hexdigest()
    with patch("app.rag.doc_store._extract_pdf", return_value=["texte doc A"]):
        ds.ingest_bytes(content_a, "a.pdf")
    with patch("app.rag.doc_store._extract_pdf", return_value=["texte doc B"]):
        ds.ingest_bytes(content_b, "b.pdf")
    total_before = ds.chunk_count
    ds.clear(doc_id_a)
    assert ds.chunk_count < total_before
    assert ds.doc_count == 1


# ── counts ───────────────────────────────────────────────────────────────────

def test_doc_count():
    ds = _make_store()
    assert ds.doc_count == 0
    with patch("app.rag.doc_store._extract_pdf", return_value=["texte"]):
        ds.ingest_bytes(b"aaa", "a.pdf")
        ds.ingest_bytes(b"bbb", "b.pdf")
    assert ds.doc_count == 2


def test_chunk_count():
    ds = _make_store()
    assert ds.chunk_count == 0
    with patch("app.rag.doc_store._extract_pdf", return_value=["texte " * 200]):
        n = ds.ingest_bytes(b"content", "doc.pdf")
    assert ds.chunk_count == n

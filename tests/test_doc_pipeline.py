"""Tests for app.rag.doc_pipeline."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from app.rag.doc_pipeline import IngestResult, _safe_table_name, ingest_document


# ── _safe_table_name ──────────────────────────────────────────────────────────

def test_safe_table_name_basic():
    name = _safe_table_name("report", 2, 0)
    assert name == "report_p2_t0"


def test_safe_table_name_special_chars():
    name = _safe_table_name("my-report 2026", 1, 1)
    assert " " not in name
    assert "-" not in name


def test_safe_table_name_leading_digit():
    name = _safe_table_name("123file", 1, 0)
    assert not name[0].isdigit()


# ── ingest_document ───────────────────────────────────────────────────────────

def _make_mock_table(confidence: float, nrows: int = 3):
    t = MagicMock()
    t.confidence = confidence
    t.page = 1
    t.table_index = 0
    t.df = pd.DataFrame({"col_a": ["x"] * nrows, "col_b": ["y"] * nrows})
    return t


def test_ingest_document_returns_ingest_result(tmp_path):
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF fake")

    mock_doc_store = MagicMock()
    mock_doc_store.ingest.return_value = 5

    with patch("app.rag.doc_pipeline.extract_tables_from_pdf", return_value=[]):
        result = ingest_document(pdf, mock_doc_store)

    assert isinstance(result, IngestResult)
    assert result.text_chunks == 5
    assert result.tables_found == 0


def test_ingest_document_counts_text_chunks(tmp_path):
    docx = tmp_path / "doc.docx"
    docx.write_bytes(b"PK fake")

    mock_doc_store = MagicMock()
    mock_doc_store.ingest.return_value = 12

    with patch("app.rag.doc_pipeline.extract_tables_from_docx", return_value=[]):
        result = ingest_document(docx, mock_doc_store)

    assert result.text_chunks == 12


def test_ingest_document_loads_high_confidence_tables(tmp_path):
    pdf = tmp_path / "report.pdf"
    pdf.write_bytes(b"%PDF fake")

    mock_doc_store = MagicMock()
    mock_doc_store.ingest.return_value = 3

    mock_data_store = MagicMock()
    high_conf_table = _make_mock_table(confidence=0.8)

    with patch("app.rag.doc_pipeline.extract_tables_from_pdf", return_value=[high_conf_table]):
        result = ingest_document(pdf, mock_doc_store, mock_data_store)

    assert result.tables_found == 1
    assert result.tables_loaded == 1
    mock_data_store.load_dataframe.assert_called_once()


def test_ingest_document_skips_low_confidence_tables(tmp_path):
    pdf = tmp_path / "report.pdf"
    pdf.write_bytes(b"%PDF fake")

    mock_doc_store = MagicMock()
    mock_doc_store.ingest.return_value = 2

    mock_data_store = MagicMock()
    low_conf_table = _make_mock_table(confidence=0.3)

    with patch("app.rag.doc_pipeline.extract_tables_from_pdf", return_value=[low_conf_table]):
        result = ingest_document(pdf, mock_doc_store, mock_data_store)

    assert result.tables_found == 1
    assert result.tables_loaded == 0
    mock_data_store.load_dataframe.assert_not_called()


def test_ingest_document_no_data_store_tables_not_loaded(tmp_path):
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF fake")

    mock_doc_store = MagicMock()
    mock_doc_store.ingest.return_value = 4
    high_conf = _make_mock_table(confidence=0.9)

    with patch("app.rag.doc_pipeline.extract_tables_from_pdf", return_value=[high_conf]):
        result = ingest_document(pdf, mock_doc_store, data_store=None)

    assert result.tables_found == 1
    assert result.tables_loaded == 0


def test_ingest_result_errors_captured(tmp_path):
    pdf = tmp_path / "bad.pdf"
    pdf.write_bytes(b"%PDF fake")

    mock_doc_store = MagicMock()
    mock_doc_store.ingest.side_effect = RuntimeError("parse error")

    with patch("app.rag.doc_pipeline.extract_tables_from_pdf", return_value=[]):
        result = ingest_document(pdf, mock_doc_store)

    assert result.text_chunks == 0
    assert any("text extraction" in e for e in result.errors)


def test_ingest_document_source_name(tmp_path):
    pdf = tmp_path / "annual_report.pdf"
    pdf.write_bytes(b"%PDF fake")

    mock_doc_store = MagicMock()
    mock_doc_store.ingest.return_value = 1

    with patch("app.rag.doc_pipeline.extract_tables_from_pdf", return_value=[]):
        result = ingest_document(pdf, mock_doc_store)

    assert result.source == "annual_report.pdf"

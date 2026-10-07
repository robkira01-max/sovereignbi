"""Tests for app.rag.table_extractor."""
from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from app.rag.table_extractor import (
    ExtractedTable,
    _confidence,
    _parse_tabular_lines,
    extract_tables_from_docx,
    extract_tables_from_pdf,
    tables_to_datastore_summary,
)


# ── _parse_tabular_lines ──────────────────────────────────────────────────────

def test_parse_tabular_lines_basic():
    lines = ["Region    Ventes    Part", "Ontario   12000     0.34", "Quebec    8500      0.24"]
    df = _parse_tabular_lines(lines)
    assert df is not None
    assert list(df.columns) == ["Region", "Ventes", "Part"]
    assert len(df) == 2


def test_parse_tabular_lines_returns_none_for_single_column():
    lines = ["OnlyOneToken", "AnotherSingle"]
    df = _parse_tabular_lines(lines)
    assert df is None


def test_parse_tabular_lines_returns_none_for_single_row():
    lines = ["Col1    Col2    Col3"]
    df = _parse_tabular_lines(lines)
    assert df is None


def test_confidence_all_filled():
    df = pd.DataFrame({"a": ["x", "y"], "b": ["1", "2"]})
    assert _confidence(df) == 1.0


def test_confidence_half_empty():
    df = pd.DataFrame({"a": ["x", ""], "b": ["1", ""]})
    assert _confidence(df) == 0.5


def test_confidence_empty_df():
    df = pd.DataFrame()
    assert _confidence(df) == 0.0


# ── extract_tables_from_pdf ───────────────────────────────────────────────────

def _make_mock_pdf_page(text: str):
    page = MagicMock()
    page.extract_text.return_value = text
    return page


def test_extract_tables_from_pdf_finds_table(tmp_path):
    tabular_text = "Region      Ventes      Part\nOntario     12000       0.34\nQuebec      8500        0.24"
    mock_reader = MagicMock()
    mock_reader.pages = [_make_mock_pdf_page(tabular_text)]

    pdf_path = tmp_path / "test.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake")

    with patch("app.rag.table_extractor.PdfReader", return_value=mock_reader):
        tables = extract_tables_from_pdf(pdf_path)

    assert len(tables) >= 1
    assert tables[0].source == "test.pdf"
    assert tables[0].page == 1
    assert len(tables[0].df.columns) >= 2


def test_extract_tables_from_pdf_empty_page(tmp_path):
    mock_reader = MagicMock()
    mock_reader.pages = [_make_mock_pdf_page("No tabular content here at all.")]

    pdf_path = tmp_path / "empty.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake")

    with patch("app.rag.table_extractor.PdfReader", return_value=mock_reader):
        tables = extract_tables_from_pdf(pdf_path)

    assert tables == []


# ── extract_tables_from_docx ──────────────────────────────────────────────────

def _make_mock_docx_table(rows: list[list[str]]):
    table = MagicMock()
    mock_rows = []
    for row_data in rows:
        row = MagicMock()
        cells = [MagicMock(text=cell) for cell in row_data]
        row.cells = cells
        mock_rows.append(row)
    table.rows = mock_rows
    return table


def test_extract_tables_from_docx_simple(tmp_path):
    rows = [["Region", "Ventes"], ["Ontario", "12000"], ["Quebec", "8500"]]
    mock_doc = MagicMock()
    mock_doc.tables = [_make_mock_docx_table(rows)]

    docx_path = tmp_path / "test.docx"
    docx_path.write_bytes(b"PK fake docx")

    with patch("app.rag.table_extractor.docx.Document", return_value=mock_doc):
        tables = extract_tables_from_docx(docx_path)

    assert len(tables) == 1
    assert list(tables[0].df.columns) == ["Region", "Ventes"]
    assert len(tables[0].df) == 2
    assert tables[0].confidence > 0


def test_extract_tables_from_docx_ignores_single_column(tmp_path):
    rows = [["Header"], ["Value1"], ["Value2"]]
    mock_doc = MagicMock()
    mock_doc.tables = [_make_mock_docx_table(rows)]

    docx_path = tmp_path / "narrow.docx"
    docx_path.write_bytes(b"PK fake docx")

    with patch("app.rag.table_extractor.docx.Document", return_value=mock_doc):
        tables = extract_tables_from_docx(docx_path)

    assert tables == []


def test_extract_tables_from_docx_empty(tmp_path):
    mock_doc = MagicMock()
    mock_doc.tables = []

    docx_path = tmp_path / "empty.docx"
    docx_path.write_bytes(b"PK fake docx")

    with patch("app.rag.table_extractor.docx.Document", return_value=mock_doc):
        tables = extract_tables_from_docx(docx_path)

    assert tables == []


# ── tables_to_datastore_summary ───────────────────────────────────────────────

def test_tables_to_datastore_summary_format():
    df = pd.DataFrame({"region": ["Ontario"], "ventes": [12000]})
    table = ExtractedTable(source="data.pdf", page=2, table_index=0, df=df, confidence=0.9)
    summary = tables_to_datastore_summary([table])
    assert "data.pdf" in summary
    assert "p.2" in summary
    assert "region" in summary


def test_tables_to_datastore_summary_empty():
    assert tables_to_datastore_summary([]) == ""

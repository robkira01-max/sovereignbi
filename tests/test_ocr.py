"""Tests for app.rag.ocr."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def _make_mock_reader(texts: list[str]):
    reader = MagicMock()
    pages = []
    for t in texts:
        page = MagicMock()
        page.extract_text.return_value = t
        pages.append(page)
    reader.pages = pages
    return reader


# ── is_text_pdf ───────────────────────────────────────────────────────────────

def test_is_text_pdf_true_for_text_rich(tmp_path):
    pdf_path = tmp_path / "text.pdf"
    pdf_path.write_bytes(b"%PDF fake")
    long_text = "A" * 200
    mock_reader = _make_mock_reader([long_text])
    with patch("app.rag.ocr.PdfReader", return_value=mock_reader):
        from app.rag.ocr import is_text_pdf
        assert is_text_pdf(pdf_path) is True


def test_is_text_pdf_false_for_empty(tmp_path):
    pdf_path = tmp_path / "scanned.pdf"
    pdf_path.write_bytes(b"%PDF fake")
    mock_reader = _make_mock_reader(["", ""])
    with patch("app.rag.ocr.PdfReader", return_value=mock_reader):
        from app.rag.ocr import is_text_pdf
        assert is_text_pdf(pdf_path) is False


# ── ocr_pdf ───────────────────────────────────────────────────────────────────

def test_ocr_pdf_raises_import_error_if_no_tesseract(tmp_path):
    """ocr_pdf raises ImportError when pytesseract module is None."""
    pdf_path = tmp_path / "scan.pdf"
    pdf_path.write_bytes(b"%PDF fake")
    import app.rag.ocr as ocr_mod
    with patch.object(ocr_mod, "pytesseract", None), \
         patch.object(ocr_mod, "convert_from_bytes", None):
        with pytest.raises(ImportError):
            ocr_mod.ocr_pdf(pdf_path)


def test_ocr_pdf_returns_list_of_strings(tmp_path):
    pdf_path = tmp_path / "doc.pdf"
    pdf_path.write_bytes(b"%PDF fake")

    mock_img = MagicMock()
    mock_tess = MagicMock()
    mock_tess.image_to_string.return_value = "Extracted text"
    mock_convert = MagicMock(return_value=[mock_img, mock_img])

    import app.rag.ocr as ocr_mod
    with patch.object(ocr_mod, "convert_from_bytes", mock_convert), \
         patch.object(ocr_mod, "pytesseract", mock_tess):
        result = ocr_mod.ocr_pdf(pdf_path)

    assert isinstance(result, list)
    assert len(result) == 2
    assert all(isinstance(t, str) for t in result)


# ── extract_text_with_fallback ────────────────────────────────────────────────

def test_extract_text_with_fallback_uses_pypdf_when_sufficient(tmp_path):
    pdf_path = tmp_path / "text.pdf"
    pdf_path.write_bytes(b"%PDF fake")
    long_text = "B" * 300
    mock_reader = _make_mock_reader([long_text])
    with patch("app.rag.ocr.PdfReader", return_value=mock_reader):
        from app.rag.ocr import extract_text_with_fallback
        result = extract_text_with_fallback(pdf_path)
    assert result == [long_text]


def test_extract_text_with_fallback_graceful_when_ocr_unavailable(tmp_path):
    pdf_path = tmp_path / "scan.pdf"
    pdf_path.write_bytes(b"%PDF fake")
    mock_reader = _make_mock_reader(["short"])
    with patch("app.rag.ocr.PdfReader", return_value=mock_reader), \
         patch("app.rag.ocr.ocr_pdf", side_effect=ImportError("no tesseract")):
        from app.rag.ocr import extract_text_with_fallback
        result = extract_text_with_fallback(pdf_path)
    assert isinstance(result, list)


def test_extract_text_with_fallback_returns_list_of_strings(tmp_path):
    pdf_path = tmp_path / "doc.pdf"
    pdf_path.write_bytes(b"%PDF fake")
    mock_reader = _make_mock_reader(["Hello world " * 10, "Page 2 " * 10])
    with patch("app.rag.ocr.PdfReader", return_value=mock_reader):
        from app.rag.ocr import extract_text_with_fallback
        result = extract_text_with_fallback(pdf_path)
    assert isinstance(result, list)
    assert all(isinstance(t, str) for t in result)

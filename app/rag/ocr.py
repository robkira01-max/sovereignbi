"""OCR des PDF numérisés — fallback quand pypdf ne trouve pas de texte."""
from __future__ import annotations

import io
import logging
from pathlib import Path

from pypdf import PdfReader

try:
    import pytesseract
    from pdf2image import convert_from_bytes
    _OCR_AVAILABLE = True
except ImportError:
    pytesseract = None  # type: ignore[assignment]
    convert_from_bytes = None  # type: ignore[assignment]
    _OCR_AVAILABLE = False

logger = logging.getLogger(__name__)

_MIN_CHARS = 50


def is_text_pdf(path: str | Path, min_chars_per_page: int = _MIN_CHARS) -> bool:
    """Return True if the PDF has extractable text (not scanned)."""
    content = Path(path).read_bytes()
    reader = PdfReader(io.BytesIO(content))
    if not reader.pages:
        return False
    total_chars = sum(len(p.extract_text() or "") for p in reader.pages)
    return total_chars >= min_chars_per_page * len(reader.pages)


def ocr_pdf(path: str | Path, lang: str = "fra+eng") -> list[str]:
    """OCR a PDF page by page using pdf2image + pytesseract.

    Raises ImportError if Tesseract/pdf2image is not installed.
    """
    if pytesseract is None or convert_from_bytes is None:
        raise ImportError(
            "OCR requires pytesseract and pdf2image. "
            "Install Tesseract system binary and run: pip install pytesseract pdf2image Pillow"
        )

    content = Path(path).read_bytes()
    try:
        images = convert_from_bytes(content)
    except Exception as exc:
        raise RuntimeError(f"pdf2image failed: {exc}") from exc

    texts: list[str] = []
    for img in images:
        try:
            text = pytesseract.image_to_string(img, lang=lang)
        except Exception as exc:
            logger.warning("pytesseract failed on page: %s", exc)
            text = ""
        texts.append(text)
    return texts


def extract_text_with_fallback(path: str | Path) -> list[str]:
    """Extract text from PDF: try pypdf first, fall back to OCR if too short."""
    p = Path(path)
    content = p.read_bytes()
    reader = PdfReader(io.BytesIO(content))
    pages_text = [page.extract_text() or "" for page in reader.pages]
    total = sum(len(t) for t in pages_text)

    if total >= _MIN_CHARS * max(len(pages_text), 1):
        return pages_text

    try:
        return ocr_pdf(p)
    except ImportError:
        logger.warning(
            "PDF %s appears scanned but Tesseract is not installed. "
            "Returning partial text.",
            p.name,
        )
        return pages_text
    except Exception as exc:
        logger.warning("OCR failed for %s: %s. Using partial text.", p.name, exc)
        return pages_text

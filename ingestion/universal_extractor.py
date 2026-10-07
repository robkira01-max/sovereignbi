"""Universal extractor: PDF, image (PNG/JPEG), Excel/CSV → ExtractedStructure."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Sector keyword maps
_SECTOR_KEYWORDS: dict[str, list[str]] = {
    "humanitaire": ["migrant", "flux", "déplacement", "fmp", "oim", "unhcr", "réfugié",
                    "refugee", "displacement", "migration", "humanitarian", "mouvement"],
    "finance": ["revenu", "dépense", "bilan", "trésorerie", "comptable", "ohada",
                "budget", "facture", "invoice", "revenue", "expense", "cash"],
    "médecine": ["patient", "consultation", "diagnostic", "morbidité", "épidémio",
                 "hospital", "clinic", "disease", "health", "santé"],
    "ingénierie": ["production", "équipement", "maintenance", "panne", "rendement",
                   "machine", "sensor", "capteur", "uptime", "defect"],
    "commerce": ["vente", "client", "commande", "produit", "stock", "sale", "order",
                 "customer", "inventory"],
}

_SECTION_KEYWORDS = {
    "APERÇU", "DÉMOGRAPHIE", "VULNÉRABILITÉS", "DESTINATIONS", "TRANSPORT",
    "NATIONALITÉS", "ARRIVÉES", "RÉSUMÉ", "OVERVIEW", "SUMMARY", "DEMOGRAPHICS",
    "ANALYSIS", "ANALYSE", "INDICATEURS", "KPI", "RÉSULTATS", "CONCLUSIONS",
}

# Numbers with 3+ digits (possibly space-separated like "12 182")
_KPI_NUMBER_RE = re.compile(r"\b(\d[\d\s]{2,}|\d{3,})\b")
_UPPERCASE_LINE_RE = re.compile(r"^[A-ZÀÂÄÉÈÊËÎÏÔÙÛÜÇ\s\-/]{4,}$")


@dataclass
class ExtractedKPI:
    value: str
    label: str


@dataclass
class ExtractedSection:
    title: str
    content: str


@dataclass
class ExtractedStructure:
    title: str
    kpis: list[ExtractedKPI] = field(default_factory=list)
    sections: list[ExtractedSection] = field(default_factory=list)
    column_names: list[str] = field(default_factory=list)
    detected_sector: str = "général"
    raw_text: str = ""


def _detect_sector(text: str) -> str:
    text_lower = text.lower()
    scores: dict[str, int] = {}
    for sector, keywords in _SECTOR_KEYWORDS.items():
        scores[sector] = sum(1 for kw in keywords if kw in text_lower)
    best = max(scores, key=lambda s: scores[s])
    return best if scores[best] > 0 else "général"


def _parse_text_to_structure(text: str, title: str = "") -> ExtractedStructure:
    """Common text → structure parser used by PDF and image extractors."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not title and lines:
        title = lines[0][:100]

    kpis: list[ExtractedKPI] = []
    sections: list[ExtractedSection] = []
    seen_values: set[str] = set()
    current_section_title = ""
    current_section_lines: list[str] = []

    def flush_section() -> None:
        if current_section_title and current_section_lines:
            sections.append(ExtractedSection(
                title=current_section_title,
                content=" ".join(current_section_lines),
            ))

    for i, line in enumerate(lines):
        # Detect section headers
        if _UPPERCASE_LINE_RE.match(line) or line.rstrip(":") in _SECTION_KEYWORDS:
            flush_section()
            current_section_title = line.rstrip(":")
            current_section_lines = []
            continue

        # Extract KPIs: lines that are predominantly a big number
        num_match = re.match(r"^([\d\s]{3,})$", line)
        if num_match:
            raw_val = num_match.group(1).strip()
            # label = next non-number line
            label = ""
            for j in range(i + 1, min(i + 4, len(lines))):
                candidate = lines[j]
                if not re.match(r"^[\d\s]+$", candidate) and len(candidate) <= 80:
                    label = candidate[:80]
                    break
            if not label and i > 0:
                prev = lines[i - 1]
                if not re.match(r"^[\d\s]+$", prev) and len(prev) <= 80:
                    label = prev[:80]
            clean_val = raw_val.replace(" ", "")
            if clean_val not in seen_values and label:
                seen_values.add(clean_val)
                kpis.append(ExtractedKPI(value=raw_val.strip(), label=label))
            continue

        current_section_lines.append(line)

    flush_section()

    # Fallback: scan whole text for number+label pairs
    if not kpis:
        for m in _KPI_NUMBER_RE.finditer(text):
            raw = m.group(0).replace(" ", "")
            if len(raw) >= 3:
                after = text[m.end():m.end() + 100].strip()[:60]
                label = re.sub(r"[\n\r]+", " ", after).strip()
                if label and raw not in seen_values:
                    seen_values.add(raw)
                    kpis.append(ExtractedKPI(value=m.group(0).strip(), label=label[:60]))
                    if len(kpis) >= 8:
                        break

    sector = _detect_sector(text)
    return ExtractedStructure(
        title=title,
        kpis=kpis[:8],
        sections=sections[:10],
        detected_sector=sector,
        raw_text=text[:2000],
    )


def _extract_pdf(path: str) -> ExtractedStructure:
    from pypdf import PdfReader  # noqa: PLC0415

    try:
        reader = PdfReader(path)
        pages_text = [page.extract_text() or "" for page in reader.pages]
    except Exception as exc:
        return ExtractedStructure(
            title=Path(path).stem,
            detected_sector="général",
            raw_text=f"PDF error: {exc}",
        )
    full_text = "\n".join(pages_text)
    title = ""
    if pages_text:
        first_lines = [ln.strip() for ln in pages_text[0].splitlines() if ln.strip()]
        title = first_lines[0][:100] if first_lines else ""
    return _parse_text_to_structure(full_text, title=title)


def _extract_image(path: str) -> ExtractedStructure:
    try:
        import pytesseract  # noqa: PLC0415
        from PIL import Image  # noqa: PLC0415
        img = Image.open(path)
        text = pytesseract.image_to_string(img, lang="fra+eng")
    except Exception as exc:
        return ExtractedStructure(
            title="Image non lisible",
            detected_sector="général",
            raw_text=f"OCR error: {exc}",
        )
    return _parse_text_to_structure(text)


def _extract_excel(path: str) -> ExtractedStructure:
    import pandas as pd  # noqa: PLC0415

    ext = Path(path).suffix.lower()
    try:
        if ext == ".csv":
            df = pd.read_csv(path, nrows=1000)
        else:
            df = pd.read_excel(path, nrows=1000)
    except Exception as exc:
        return ExtractedStructure(
            title=Path(path).stem,
            detected_sector="général",
            raw_text=f"Read error: {exc}",
        )

    col_names = list(df.columns)
    kpis: list[ExtractedKPI] = []
    sections: list[ExtractedSection] = []

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    date_cols = [c for c in df.columns
                 if "date" in str(c).lower() or "jour" in str(c).lower()
                 or pd.api.types.is_datetime64_any_dtype(df[c])]
    cat_cols = [c for c in df.columns
                if c not in numeric_cols and c not in date_cols
                and df[c].nunique() < 20]

    for col in numeric_cols[:6]:
        total = df[col].sum()
        label = str(col)[:60]
        kpis.append(ExtractedKPI(value=str(int(total) if float(total) == int(total) else round(total, 2)), label=label))

    if date_cols and numeric_cols:
        dc = date_cols[0]
        mc = numeric_cols[0]
        sections.append(ExtractedSection(
            title=f"Évolution temporelle",
            content=f"Évolution de {mc} par {dc}",
        ))

    for col in cat_cols[:4]:
        sections.append(ExtractedSection(
            title=f"Répartition {col}",
            content=f"Répartition par {col}",
        ))

    all_text = " ".join(str(c) for c in col_names)
    sector = _detect_sector(all_text)

    return ExtractedStructure(
        title=Path(path).stem,
        kpis=kpis,
        sections=sections,
        column_names=col_names,
        detected_sector=sector,
        raw_text=all_text[:500],
    )


_SUPPORTED = {
    ".pdf": _extract_pdf,
    ".png": _extract_image,
    ".jpg": _extract_image,
    ".jpeg": _extract_image,
    ".xlsx": _extract_excel,
    ".xls": _extract_excel,
    ".csv": _extract_excel,
}


class UniversalExtractor:
    def extract(self, file_path: str, filename: str = "") -> ExtractedStructure:
        fname = filename or file_path
        ext = Path(fname).suffix.lower()
        handler = _SUPPORTED.get(ext)
        if handler is None:
            raise ValueError(f"Format non supporté : {ext!r}")
        result = handler(file_path)
        # Use the original filename stem as title when a filename was given
        if filename:
            stem = Path(filename).stem
            if stem and (not result.title or result.title == Path(file_path).stem):
                result.title = stem
        return result

    @staticmethod
    def supported_extensions() -> list[str]:
        return list(_SUPPORTED.keys())

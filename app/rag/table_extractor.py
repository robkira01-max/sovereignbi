"""Extraction de tableaux depuis PDF et DOCX → DataFrame."""
from __future__ import annotations

import io
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from pypdf import PdfReader
import docx


@dataclass
class ExtractedTable:
    source: str
    page: int
    table_index: int
    df: pd.DataFrame
    confidence: float  # 0.0–1.0


def _parse_tabular_lines(lines: list[str]) -> pd.DataFrame | None:
    """Parse lines that look tabular (2+ tokens separated by 2+ spaces)."""
    rows: list[list[str]] = []
    for line in lines:
        cells = re.split(r" {2,}|\t", line.strip())
        cells = [c.strip() for c in cells if c.strip()]
        if len(cells) >= 2:
            rows.append(cells)
    if len(rows) < 2:
        return None
    # normalize row widths
    ncols = max(len(r) for r in rows)
    if ncols < 2:
        return None
    rows = [r + [""] * (ncols - len(r)) for r in rows]
    # first row as header if all cells look like labels (no digits dominating)
    first = rows[0]
    looks_like_header = all(not re.match(r"^\d+\.?\d*$", c) for c in first if c)
    if looks_like_header:
        df = pd.DataFrame(rows[1:], columns=first)
    else:
        df = pd.DataFrame(rows, columns=[f"col_{i}" for i in range(ncols)])
    return df


def _confidence(df: pd.DataFrame) -> float:
    total = df.size
    if total == 0:
        return 0.0
    non_empty = (df != "").sum().sum()
    return float(non_empty) / total


def extract_tables_from_pdf(path: str | Path) -> list[ExtractedTable]:
    """Extract tables from PDF using whitespace heuristic."""
    p = Path(path)
    content = p.read_bytes()
    reader = PdfReader(io.BytesIO(content))
    results: list[ExtractedTable] = []

    for page_num, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        lines = text.splitlines()
        # collect runs of tabular-looking lines
        block: list[str] = []
        table_idx = 0
        for line in lines:
            cells = re.split(r" {2,}|\t", line.strip())
            cells = [c.strip() for c in cells if c.strip()]
            if len(cells) >= 2:
                block.append(line)
            else:
                if block:
                    df = _parse_tabular_lines(block)
                    if df is not None and len(df) >= 1 and len(df.columns) >= 2:
                        results.append(ExtractedTable(
                            source=p.name,
                            page=page_num,
                            table_index=table_idx,
                            df=df,
                            confidence=_confidence(df),
                        ))
                        table_idx += 1
                    block = []
        if block:
            df = _parse_tabular_lines(block)
            if df is not None and len(df) >= 1 and len(df.columns) >= 2:
                results.append(ExtractedTable(
                    source=p.name,
                    page=page_num,
                    table_index=table_idx,
                    df=df,
                    confidence=_confidence(df),
                ))

    return results


def extract_tables_from_docx(path: str | Path) -> list[ExtractedTable]:
    """Extract tables from DOCX using python-docx API."""
    p = Path(path)
    content = p.read_bytes()
    doc = docx.Document(io.BytesIO(content))
    results: list[ExtractedTable] = []

    for table_idx, table in enumerate(doc.tables):
        rows_data: list[list[str]] = []
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            rows_data.append(cells)

        if len(rows_data) < 2 or (rows_data and len(rows_data[0]) < 2):
            continue

        ncols = max(len(r) for r in rows_data)
        rows_data = [r + [""] * (ncols - len(r)) for r in rows_data]

        first = rows_data[0]
        looks_like_header = all(not re.match(r"^\d+\.?\d*$", c) for c in first if c)
        if looks_like_header:
            df = pd.DataFrame(rows_data[1:], columns=first)
        else:
            df = pd.DataFrame(rows_data, columns=[f"col_{i}" for i in range(ncols)])

        results.append(ExtractedTable(
            source=p.name,
            page=1,
            table_index=table_idx,
            df=df,
            confidence=_confidence(df),
        ))

    return results


def tables_to_datastore_summary(tables: list[ExtractedTable]) -> str:
    if not tables:
        return ""
    lines = [f"Tableaux extraits de {tables[0].source} :"]
    for t in tables:
        cols = ", ".join(str(c) for c in t.df.columns)
        nrows = len(t.df)
        sample = ""
        if nrows > 0:
            sample_row = t.df.iloc[0].tolist()
            sample = " | ".join(str(v) for v in sample_row[:5])
        lines.append(f"  [p.{t.page}, t.{t.table_index + 1}] colonnes: {cols} ({nrows} lignes)")
        if sample:
            lines.append(f"    exemple: {sample}")
    return "\n".join(lines)

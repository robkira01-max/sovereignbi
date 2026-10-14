"""HXL (Humanitarian Exchange Language) CSV parser.

HXL CSVs have:
  Row 0: human-readable headers  (e.g. "Beneficiary ID")
  Row 1: HXL hashtag headers     (e.g. "#beneficiary+id")
  Row 2+: data

This module strips the hashtag row and exposes the mapping.
"""
from __future__ import annotations

import re
from io import StringIO
from typing import IO

import pandas as pd


_HXL_RE = re.compile(r"^#[a-z]")


def _is_hxl_row(row: list) -> bool:
    """True if at least half the non-empty cells start with '#'."""
    cells = [str(c).strip() for c in row if str(c).strip()]
    if not cells:
        return False
    matching = sum(1 for c in cells if _HXL_RE.match(c))
    return matching / len(cells) >= 0.5


def detect_hxl_row(rows: list[list]) -> int | None:
    """Return index of the HXL hashtag row, or None."""
    for i, row in enumerate(rows[:5]):
        if _is_hxl_row(row):
            return i
    return None


def hxl_to_friendly_name(tag: str) -> str:
    """'#beneficiary+count' → 'beneficiary_count'."""
    tag = tag.strip().lstrip("#")
    return re.sub(r"[^a-z0-9]+", "_", tag).strip("_")


def strip_hxl(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str]]:
    """Remove the HXL hashtag row from a DataFrame.

    Returns (clean_df, hxl_map) where hxl_map maps column name → HXL tag.
    If no hashtag row is found, returns (df, {}).
    """
    if df.empty:
        return df, {}

    rows = df.values.tolist()
    hxl_idx = detect_hxl_row(rows)
    if hxl_idx is None:
        return df, {}

    hxl_row = rows[hxl_idx]
    hxl_map: dict[str, str] = {}
    for col, tag in zip(df.columns, hxl_row):
        tag_str = str(tag).strip()
        if _HXL_RE.match(tag_str):
            hxl_map[str(col)] = tag_str

    clean_df = df.drop(index=df.index[hxl_idx]).reset_index(drop=True)
    return clean_df, hxl_map


def read_hxl_csv(
    source: str | IO,
    encoding: str = "utf-8-sig",
) -> tuple[pd.DataFrame, dict[str, str]]:
    """Read a CSV file that may contain HXL hashtags.

    Returns (data_df, hxl_map).
    The data_df has human-readable column headers; hxl_map maps col → tag.
    """
    if isinstance(source, str):
        raw = source
        df_raw = pd.read_csv(StringIO(raw), header=0, dtype=str, keep_default_na=False)
    else:
        df_raw = pd.read_csv(source, header=0, dtype=str, keep_default_na=False, encoding=encoding)

    return strip_hxl(df_raw)

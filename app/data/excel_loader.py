"""Chargeur Excel robuste : en-têtes multi-lignes, cellules fusionnées, feuilles multiples.

Stratégie :
- Détecter la ligne d'en-tête (première ligne non vide avec plusieurs colonnes non-NaN).
- Aplatir les en-têtes multi-niveaux (MultiIndex → chaîne jointe par « _ »).
- Propager les cellules fusionnées (ffill sur les colonnes et les lignes d'en-tête).
- Ignorer les feuilles vides ou purement de mise en page (< 2 colonnes non-NaN).
"""
from pathlib import Path

import pandas as pd


_MIN_COLS = 2
_MAX_HEADER_ROWS = 5


def load_excel(path: str | Path, sheet_name: str | None = None) -> dict[str, pd.DataFrame]:
    """Charge un fichier Excel. Retourne un dict {nom_feuille: DataFrame}.

    Si sheet_name est fourni, charge uniquement cette feuille.
    """
    p = Path(path)
    if p.suffix.lower() not in {".xlsx", ".xlsm", ".xls"}:
        raise ValueError(f"Format non supporté : {p.suffix}")

    raw: dict[str, pd.DataFrame] = pd.read_excel(
        p,
        sheet_name=sheet_name or None,
        header=None,
        dtype=str,
    )
    if isinstance(raw, pd.DataFrame):
        raw = {sheet_name if sheet_name else p.stem: raw}

    result: dict[str, pd.DataFrame] = {}
    for name, df in raw.items():
        cleaned = _clean_sheet(df)
        if cleaned is not None:
            result[name] = cleaned
    return result


def _clean_sheet(df: pd.DataFrame) -> pd.DataFrame | None:
    """Nettoie une feuille brute (header=None) et retourne un DataFrame exploitable."""
    if df.empty:
        return None

    df = df.copy()
    df = df.where(df.notna(), None)

    header_row = _detect_header_row(df)
    if header_row is None:
        return None

    n_header = _count_header_rows(df, header_row)
    header_block = df.iloc[header_row : header_row + n_header].copy()
    data_block = df.iloc[header_row + n_header :].copy()

    if data_block.empty:
        return None

    col_names = _build_column_names(header_block)
    data_block.columns = col_names
    data_block = data_block.reset_index(drop=True)
    data_block = _coerce_types(data_block)

    if len(data_block.columns) < _MIN_COLS:
        return None

    return data_block


def _detect_header_row(df: pd.DataFrame) -> int | None:
    """Retourne l'index de la ligne d'en-tête (première ligne avec ≥ MIN_COLS valeurs)."""
    for i, row in df.iterrows():
        non_null = row.notna().sum()
        if non_null >= _MIN_COLS:
            return int(str(i))
    return None


def _count_header_rows(df: pd.DataFrame, start: int) -> int:
    """Détecte si les colonnes s'étendent sur plusieurs lignes (en-têtes hiérarchiques)."""
    for n in range(1, _MAX_HEADER_ROWS + 1):
        end = start + n
        if end >= len(df):
            return n
        next_row = df.iloc[end]
        non_null_ratio = next_row.notna().sum() / max(len(next_row), 1)
        if non_null_ratio > 0.5:
            return n
    return 1


def _build_column_names(header_block: pd.DataFrame) -> list[str]:
    """Aplatit un bloc d'en-tête (1 ou plusieurs lignes) en liste de noms de colonnes."""
    block = header_block.ffill(axis=1).fillna("")
    if len(block) == 1:
        parts = [str(v).strip() for v in block.iloc[0]]
    else:
        parts = [
            "_".join(str(block.iloc[r, c]).strip() for r in range(len(block)) if str(block.iloc[r, c]).strip())
            for c in range(len(block.columns))
        ]

    seen: dict[str, int] = {}
    result = []
    for name in parts:
        name = name or "col"
        name = _safe_name(name)
        if name in seen:
            seen[name] += 1
            result.append(f"{name}_{seen[name]}")
        else:
            seen[name] = 0
            result.append(name)
    return result


def _safe_name(s: str) -> str:
    import re
    name = re.sub(r"\W+", "_", s.strip().lower()).strip("_")
    return name if name and not name[0].isdigit() else f"col_{name}"


def _coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    """Convertit les colonnes vers les types numériques/date quand possible."""
    for col in df.columns:
        series = df[col]
        try:
            df[col] = pd.to_numeric(series)
            continue
        except (ValueError, TypeError):
            pass
        try:
            converted = pd.to_datetime(series, infer_datetime_format=True, errors="coerce")
            if converted.notna().sum() / max(len(converted), 1) > 0.5:
                df[col] = converted
                continue
        except Exception:
            pass
    return df

"""Tests — app/data/excel_loader.py (Sprint 2)."""
from pathlib import Path

import pandas as pd
import pytest

from app.data.excel_loader import load_excel
from app.data.duckdb_store import DataStore

FIXTURES = Path(__file__).parent.parent / "eval" / "fixtures"


# ── Chargement des classeurs ──────────────────────────────────────────────────

def test_load_simple_xlsx():
    result = load_excel(FIXTURES / "classeur_simple.xlsx")
    assert len(result) == 1
    df = next(iter(result.values()))
    assert df.shape[0] == 3
    assert df.shape[1] == 3


def test_load_simple_xlsx_columns_are_strings():
    result = load_excel(FIXTURES / "classeur_simple.xlsx")
    df = next(iter(result.values()))
    assert all(isinstance(c, str) for c in df.columns)


def test_load_multi_header_no_multiindex():
    result = load_excel(FIXTURES / "classeur_en_tetes_multi.xlsx")
    assert len(result) == 1
    df = next(iter(result.values()))
    # Colonnes aplaties — pas de MultiIndex (Index uniquement)
    assert not isinstance(df.columns, pd.MultiIndex)
    assert all(isinstance(c, str) for c in df.columns)


def test_load_multi_header_has_data_rows():
    result = load_excel(FIXTURES / "classeur_en_tetes_multi.xlsx")
    df = next(iter(result.values()))
    assert len(df) >= 2


def test_load_multi_sheet_returns_all_sheets():
    result = load_excel(FIXTURES / "classeur_multi_feuilles.xlsx")
    assert len(result) == 3


def test_load_multi_sheet_names():
    result = load_excel(FIXTURES / "classeur_multi_feuilles.xlsx")
    assert set(result.keys()) == {"Ventes", "Clients", "Résumé"}


def test_load_multi_sheet_ventes():
    result = load_excel(FIXTURES / "classeur_multi_feuilles.xlsx")
    df = result["Ventes"]
    assert len(df) == 2
    assert "montant" in df.columns or any("montant" in c for c in df.columns)


def test_load_skips_empty_leading_rows():
    result = load_excel(FIXTURES / "classeur_lignes_vides.xlsx")
    assert len(result) == 1
    df = next(iter(result.values()))
    assert len(df) >= 1
    # Pas de lignes vides dans les données
    non_null_rows = df.dropna(how="all")
    assert len(non_null_rows) >= 1


def test_load_wide_schema_col_count():
    result = load_excel(FIXTURES / "classeur_colonnes_larges.xlsx")
    assert len(result) == 1
    df = next(iter(result.values()))
    assert len(df.columns) >= 50


def test_load_wide_schema_has_data():
    result = load_excel(FIXTURES / "classeur_colonnes_larges.xlsx")
    df = next(iter(result.values()))
    assert len(df) >= 5


def test_safe_column_names_no_special_chars():
    import re
    for fname in ["classeur_simple.xlsx", "classeur_multi_feuilles.xlsx", "classeur_colonnes_larges.xlsx"]:
        result = load_excel(FIXTURES / fname)
        for df in result.values():
            for col in df.columns:
                assert re.match(r"^[a-z0-9_]+$", col), f"Colonne non sécurisée : {col!r} dans {fname}"


def test_coerce_numeric_columns():
    result = load_excel(FIXTURES / "classeur_simple.xlsx")
    df = next(iter(result.values()))
    # quantite et prix doivent être numériques
    for col in df.columns:
        if col in ("quantite", "prix"):
            assert pd.api.types.is_numeric_dtype(df[col]), f"{col} non numérique"


def test_coerce_date_columns():
    """Les colonnes de date doivent être datetime ou string (pandas 2.x StringDtype acceptable)."""
    result = load_excel(FIXTURES / "classeur_multi_feuilles.xlsx")
    df = result["Ventes"]
    date_cols = [c for c in df.columns if "date" in c.lower()]
    for col in date_cols:
        dtype = df[col].dtype
        is_dt = pd.api.types.is_datetime64_any_dtype(dtype)
        is_str = dtype == object or "string" in str(dtype).lower() or str(dtype) == "str"
        assert is_dt or is_str, f"Colonne date {col!r} dtype inattendu : {dtype}"


def test_unsupported_format_raises():
    with pytest.raises(ValueError, match="Format non supporté"):
        load_excel(FIXTURES / "dummy.txt")


def test_single_sheet_name_is_stem():
    """Pour un fichier à 1 feuille, la clé est le nom de la feuille (pas le stem du fichier)."""
    result = load_excel(FIXTURES / "classeur_simple.xlsx")
    assert len(result) == 1


def test_load_specific_sheet():
    result = load_excel(FIXTURES / "classeur_multi_feuilles.xlsx", sheet_name="Clients")
    assert "Clients" in result
    assert len(result) == 1


# ── DataStore.load_file avec Excel ────────────────────────────────────────────

def test_datastore_loads_simple_xlsx():
    store = DataStore()
    names = store.load_file(FIXTURES / "classeur_simple.xlsx")
    assert len(names) == 1
    assert names[0] in store.tables


def test_datastore_loads_multi_sheet_xlsx():
    store = DataStore()
    names = store.load_file(FIXTURES / "classeur_multi_feuilles.xlsx")
    assert len(names) == 3
    assert all(n in store.tables for n in names)


def test_datastore_wide_schema_queryable():
    store = DataStore()
    names = store.load_file(FIXTURES / "classeur_colonnes_larges.xlsx")
    table = names[0]
    cols, rows = store.execute(f'SELECT COUNT(*) FROM "{table}"')
    assert rows[0][0] >= 5


def test_datastore_loads_large_csv():
    store = DataStore()
    names = store.load_file(FIXTURES / "large_schema.csv")
    assert len(names) == 1
    cols, rows = store.execute(f'SELECT COUNT(*) FROM "{names[0]}"')
    assert rows[0][0] == 500


def test_datastore_large_csv_has_50_cols():
    store = DataStore()
    names = store.load_file(FIXTURES / "large_schema.csv")
    table = names[0]
    schema = store.schema_description()
    assert "montant_ht" in schema

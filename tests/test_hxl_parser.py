"""Tests for app/data/hxl_parser.py."""
import io
import pandas as pd
import pytest

from app.data.hxl_parser import (
    detect_hxl_row,
    hxl_to_friendly_name,
    strip_hxl,
    read_hxl_csv,
    _is_hxl_row,
)

# Minimal HXL CSV fixture
HXL_CSV = """\
Beneficiary ID,Country of Origin,Total persons
#beneficiary+id,#country+origin,#population+total
BEN-001,Somalia,4
BEN-002,Ethiopia,7
"""

# CSV without HXL hashtags
PLAIN_CSV = """\
ID,Name,Count
1,Alice,10
2,Bob,20
"""


def test_is_hxl_row_true():
    assert _is_hxl_row(["#beneficiary+id", "#country+origin", "#population+total"])


def test_is_hxl_row_false():
    assert not _is_hxl_row(["Beneficiary ID", "Country", "Total"])


def test_is_hxl_row_mixed_mostly_hxl():
    assert _is_hxl_row(["#beneficiary+id", "#country", "notes"])


def test_is_hxl_row_empty():
    assert not _is_hxl_row([])


def test_detect_hxl_row():
    rows = [
        ["Beneficiary ID", "Country", "Total"],
        ["#beneficiary+id", "#country+origin", "#population+total"],
        ["BEN-001", "Somalia", "4"],
    ]
    assert detect_hxl_row(rows) == 1


def test_detect_hxl_row_no_hxl():
    rows = [["ID", "Name"], ["1", "Alice"], ["2", "Bob"]]
    assert detect_hxl_row(rows) is None


def test_hxl_to_friendly_name_simple():
    assert hxl_to_friendly_name("#beneficiary+id") == "beneficiary_id"


def test_hxl_to_friendly_name_country():
    assert hxl_to_friendly_name("#country+origin") == "country_origin"


def test_hxl_to_friendly_name_population():
    assert hxl_to_friendly_name("#population+total") == "population_total"


def test_hxl_to_friendly_name_strips_hash():
    result = hxl_to_friendly_name("#adm1+name")
    assert not result.startswith("#")


def test_strip_hxl_removes_hashtag_row():
    df = pd.DataFrame(
        [
            ["#beneficiary+id", "#country+origin", "#population+total"],
            ["BEN-001", "Somalia", "4"],
            ["BEN-002", "Ethiopia", "7"],
        ],
        columns=["Beneficiary ID", "Country of Origin", "Total persons"],
    )
    clean, hxl_map = strip_hxl(df)
    assert len(clean) == 2
    assert "#beneficiary+id" not in clean.values.flatten()


def test_strip_hxl_returns_map():
    df = pd.DataFrame(
        [
            ["#beneficiary+id", "#country+origin"],
            ["BEN-001", "Somalia"],
        ],
        columns=["Beneficiary ID", "Country"],
    )
    _, hxl_map = strip_hxl(df)
    assert hxl_map["Beneficiary ID"] == "#beneficiary+id"
    assert hxl_map["Country"] == "#country+origin"


def test_strip_hxl_no_hashtag_row():
    df = pd.DataFrame([["1", "Alice"], ["2", "Bob"]], columns=["ID", "Name"])
    clean, hxl_map = strip_hxl(df)
    assert len(clean) == 2
    assert hxl_map == {}


def test_strip_hxl_empty_df():
    df = pd.DataFrame()
    clean, hxl_map = strip_hxl(df)
    assert clean.empty
    assert hxl_map == {}


def test_read_hxl_csv_from_string():
    df, hxl_map = read_hxl_csv(HXL_CSV)
    assert len(df) == 2
    assert "Beneficiary ID" in df.columns or len(df.columns) >= 2


def test_read_hxl_csv_map_populated():
    _, hxl_map = read_hxl_csv(HXL_CSV)
    assert len(hxl_map) >= 2


def test_read_plain_csv_no_hxl():
    df, hxl_map = read_hxl_csv(PLAIN_CSV)
    assert len(df) == 2
    assert hxl_map == {}


def test_read_hxl_csv_from_filelike():
    fobj = io.BytesIO(HXL_CSV.encode("utf-8"))
    df, hxl_map = read_hxl_csv(fobj)
    assert len(df) == 2

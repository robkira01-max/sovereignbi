"""P-066 : SDMX-CSV 2.0 — écriture et lecture."""
from __future__ import annotations

import csv
import datetime as dt
import io

import pytest

from app.sdmx.csv_format import (
    SdmxError, component_id, default_structure_id, read_sdmx_csv, to_time_period, write_sdmx_csv,
)

SID = "MIZANBI:CHOMAGE(1.0)"


def w(rows, **kw):
    cols = kw.pop("cols", ["Région", "année", "taux"])
    kw.setdefault("structure_id", SID)
    kw.setdefault("value_col", "taux")
    kw.setdefault("time_col", "année")
    return write_sdmx_csv(cols, rows, **kw)


def parsed(text):
    return list(csv.reader(io.StringIO(text)))


def test_component_id_strips_accents_and_symbols():
    assert component_id("Région") == "REGION"
    assert component_id("taux chômage (%)") == "TAUX_CHOMAGE"
    for bad in ("", "123", "%%%"):
        with pytest.raises(SdmxError):
            component_id(bad)


def test_default_structure_id_is_valid_and_readable():
    sid = default_structure_id("dash-1_kpi 2")
    assert sid == "MIZANBI:DASH_1_KPI_2(1.0)"
    write_sdmx_csv(["a", "v"], [["x", 1]], structure_id=sid, value_col="v")


def test_header_layout_follows_sdmx_csv_2():
    rows = parsed(w([["Obock", 2023, 29.1]]))
    assert rows[0] == ["STRUCTURE", "STRUCTURE_ID", "ACTION", "REGION", "TIME_PERIOD", "OBS_VALUE"]
    assert rows[1] == ["dataflow", SID, "I", "Obock", "2023", "29.1"]


def test_unit_adds_a_unit_measure_attribute_last():
    rows = parsed(w([["Obock", 2023, 29.1]], unit="PCT"))
    assert rows[0][-2:] == ["OBS_VALUE", "UNIT_MEASURE"] and rows[1][-1] == "PCT"


def test_no_time_column_means_no_time_period():
    rows = parsed(write_sdmx_csv(["r", "v"], [["a", 1]], structure_id=SID, value_col="v"))
    assert "TIME_PERIOD" not in rows[0]


def test_dates_are_converted_to_the_requested_frequency():
    d = dt.date(2024, 5, 17)
    assert to_time_period(d, "A") == "2024"
    assert to_time_period(d, "M") == "2024-05"
    assert to_time_period(d, "Q") == "2024-Q2"
    assert to_time_period(d) == "2024-05-17"
    assert to_time_period(dt.datetime(2024, 1, 2, 3), "D") == "2024-01-02"
    assert to_time_period(2024.0) == "2024" and to_time_period("2024-Q4") == "2024-Q4"


@pytest.mark.parametrize("bad", ["24", "2024-13", "2024-Q5", "hier", "2024/05", ""])
def test_invalid_time_periods_are_refused(bad):
    with pytest.raises(SdmxError):
        to_time_period(bad)


def test_obs_value_must_be_numeric_and_missing_is_empty():
    assert parsed(w([["a", 2023, None]]))[1][-1] == ""
    assert parsed(w([["a", 2023, float("nan")]]))[1][-1] == ""
    with pytest.raises(SdmxError):
        w([["a", 2023, "beaucoup"]])
    with pytest.raises(SdmxError):
        w([["a", 2023, True]])


def test_formula_injection_is_neutralised_in_text_cells():
    rows = parsed(w([["=HYPERLINK(\"x\")", 2023, 1], ["+1", 2023, 1], ["@a", 2023, 1], ["-ok", 2023, 1]]))
    assert [r[3] for r in rows[1:]] == ["'=HYPERLINK(\"x\")", "'+1", "'@a", "-ok"]


@pytest.mark.parametrize("kw,msg", [
    ({"structure_id": "chomage"}, "STRUCTURE_ID"),
    ({"structure": "autre"}, "structure"),
    ({"action": "X"}, "Action"),
    ({"value_col": "absente"}, "introuvable"),
    ({"time_col": "absente"}, "introuvable"),
])
def test_invalid_parameters_are_refused_with_a_clear_message(kw, msg):
    with pytest.raises(SdmxError) as e:
        w([["a", 2023, 1]], **kw)
    assert msg.lower() in str(e.value).lower()


def test_dimension_ids_must_be_unique_and_not_reserved():
    with pytest.raises(SdmxError):
        write_sdmx_csv(["Région", "REGION", "v"], [["a", "b", 1]], structure_id=SID, value_col="v")
    with pytest.raises(SdmxError):
        write_sdmx_csv(["action", "v"], [["a", 1]], structure_id=SID, value_col="v")


def test_round_trip_keeps_values():
    text = w([["Obock", 2023, 29.1], ["Tadjourah", 2024, 27]], unit="PCT")
    d = read_sdmx_csv(text)
    assert d.version == "2.0" and d.structure == "dataflow" and d.structure_id == SID and d.action == "I"
    assert d.columns == ["REGION", "TIME_PERIOD", "OBS_VALUE", "UNIT_MEASURE"]
    assert d.rows == [("Obock", "2023", 29.1, "PCT"), ("Tadjourah", "2024", 27.0, "PCT")]
    assert d.has_time


def test_reader_accepts_version_1_and_missing_action_and_bom():
    v1 = "DATAFLOW,REF_AREA,TIME_PERIOD,OBS_VALUE\nINSTAD:X(1.0),DJ,2023,5\n"
    d = read_sdmx_csv("﻿" + v1)
    assert d.version == "1.0" and d.structure_id == "INSTAD:X(1.0)"
    no_action = "STRUCTURE,STRUCTURE_ID,REF_AREA,OBS_VALUE\ndataflow,INSTAD:X(1.0),DJ,5\n"
    assert read_sdmx_csv(no_action).action == "I"


@pytest.mark.parametrize("text,msg", [
    ("", "vide"),
    ("a,b\n1,2\n", "STRUCTURE"),
    ("STRUCTURE,STRUCTURE_ID,ACTION,REF_AREA\ndataflow,X:Y(1.0),I,DJ\n", "OBS_VALUE"),
    ("STRUCTURE,STRUCTURE_ID,ACTION,OBS_VALUE,OBS_VALUE\ndataflow,X:Y(1.0),I,1,2\n", "double"),
    ("STRUCTURE,STRUCTURE_ID,ACTION,1BAD,OBS_VALUE\ndataflow,X:Y(1.0),I,a,2\n", "invalide"),
    ("STRUCTURE,STRUCTURE_ID,ACTION,OBS_VALUE\ndataflow,X:Y(1.0),I,abc\n", "non numérique"),
    ("STRUCTURE,STRUCTURE_ID,ACTION,OBS_VALUE\ndataflow,X:Y(1.0),I,nan\n", "invalide"),
    ("STRUCTURE,STRUCTURE_ID,ACTION,OBS_VALUE\ndataflow,X:Y(1.0),I,inf\n", "invalide"),
    ("STRUCTURE,STRUCTURE_ID,ACTION,TIME_PERIOD,OBS_VALUE\ndataflow,X:Y(1.0),I,hier,1\n", "TIME_PERIOD"),
    ("STRUCTURE,STRUCTURE_ID,ACTION,OBS_VALUE\ndataflow,X:Y(1.0),I\n", "colonnes"),
    ("STRUCTURE,STRUCTURE_ID,ACTION,OBS_VALUE\ndataflow,X:Y(1.0),Z,1\n", "action"),
    ("STRUCTURE,STRUCTURE_ID,ACTION,OBS_VALUE\nbizarre,X:Y(1.0),I,1\n", "structure"),
    ("STRUCTURE,STRUCTURE_ID,ACTION,OBS_VALUE\ndataflow,X:Y(1.0),I,1\ndataflow,X:Z(1.0),I,2\n", "un seul dataflow"),
    ("STRUCTURE,STRUCTURE_ID,ACTION,OBS_VALUE\n", "Aucune observation"),
])
def test_reader_rejects_malformed_files_with_line_numbers_or_reasons(text, msg):
    with pytest.raises(SdmxError) as e:
        read_sdmx_csv(text)
    assert msg.lower() in str(e.value).lower()


def test_error_messages_carry_the_line_number():
    with pytest.raises(SdmxError) as e:
        read_sdmx_csv("STRUCTURE,STRUCTURE_ID,ACTION,OBS_VALUE\ndataflow,X:Y(1.0),I,1\ndataflow,X:Y(1.0),I,abc\n")
    assert "Ligne 3" in str(e.value)


def test_row_limit_is_enforced_when_reading_and_writing(monkeypatch):
    body = "STRUCTURE,STRUCTURE_ID,ACTION,OBS_VALUE\n" + "dataflow,X:Y(1.0),I,1\n" * 4
    with pytest.raises(SdmxError):
        read_sdmx_csv(body, max_rows=3)
    monkeypatch.setattr("app.sdmx.csv_format.MAX_ROWS", 3)
    with pytest.raises(SdmxError):
        write_sdmx_csv(["v"], [[1]] * 4, structure_id=SID, value_col="v")


def test_decimal_observations_from_duckdb_are_written_exactly():
    from decimal import Decimal
    rows = parsed(w([["a", 2023, Decimal("29.10")]]))
    assert rows[1][-1] == "29.10"

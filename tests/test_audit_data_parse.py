"""P-074 : lecture CSV / XLSX (limites, rapports explicites, refus des fichiers ambigus)."""
from __future__ import annotations

import io
from datetime import datetime

import openpyxl
import pytest

from app.audit_data import parse
from app.audit_data.parse import TableRefused, read_csv, read_xlsx


def refused(fn, *a) -> str:
    with pytest.raises(TableRefused) as e:
        fn(*a)
    return e.value.code


def wb_bytes(build) -> bytes:
    wb = openpyxl.Workbook()
    build(wb)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ── CSV ──────────────────────────────────────────────────────────────────────

def test_csv_basic_with_line_numbers_and_meta():
    t = read_csv(b"Date;Compte;Montant\n2026-01-05;601;1 200,50\n2026-01-06;602;80\n")
    assert t.headers == ["Date", "Compte", "Montant"]
    assert t.rows == [(2, ["2026-01-05", "601", "1 200,50"]), (3, ["2026-01-06", "602", "80"])]
    assert t.meta["delimiter"] == ";" and t.meta["encoding"] == "utf-8" and "encoding_assumed" not in t.meta


@pytest.mark.parametrize("delim", [",", ";", "\t", "|"])
def test_csv_delimiters_are_detected(delim):
    t = read_csv(f"a{delim}b{delim}c\n1{delim}2{delim}3\n4{delim}5{delim}6\n".encode())
    assert t.headers == ["a", "b", "c"] and len(t.rows) == 2 and t.meta["delimiter"] == delim


def test_csv_bom_and_cp1252_are_reported_not_hidden():
    assert read_csv("﻿Date;Libellé\n2026-01-01;Café\n".encode("utf-8")).headers == ["Date", "Libellé"]
    t = read_csv("Date;Libellé\n2026-01-01;Café\n".encode("cp1252"))
    assert t.meta["encoding"] == "cp1252" and t.meta["encoding_assumed"] is True and t.rows[0][1][1] == "Café"


def test_csv_quoted_fields_with_delimiters_and_newlines():
    t = read_csv(b'a;b\n"x;y";"ligne1\nligne2"\n')
    assert t.rows[0][1] == ["x;y", "ligne1\nligne2"]


def test_csv_blank_rows_are_skipped_and_counted_and_blank_headers_renamed():
    t = read_csv(b"a;;c\n1;2;3\n\n;;\n4;5;6\n")
    assert t.headers == ["a", "colonne_2", "c"] and len(t.rows) == 2
    assert t.meta["blank_rows_skipped"] == 2 and t.meta["blank_headers_renamed"] == [2]


def test_csv_short_rows_are_padded_but_long_rows_refused():
    assert read_csv(b"a;b;c\n1;2;3\n4;5\n").rows[1][1] == ["4", "5", None]
    assert refused(read_csv, b"a;b\n1;2\n3;4;5\n") in ("ragged_row", "delimiter_undetermined")


def test_csv_ambiguous_or_broken_structures_are_refused():
    assert refused(read_csv, b"a;b\n1;2;3;4;5\n6\n") == "delimiter_undetermined"
    assert refused(read_csv, b"onlyoneword\nsecond\n") == "delimiter_undetermined"
    assert refused(read_csv, b"\n\n  \n") == "no_data"
    assert refused(read_csv, b"a;b\n") == "no_data"
    assert refused(read_csv, b"a;a\n1;2\n") == "duplicate_headers"
    assert refused(read_csv, b"A;a\n1;2\n") == "duplicate_headers"
    assert refused(read_csv, b'a;b\n"unterminated;2\n3;4\n') == "csv_malformed"
    assert refused(read_csv, b"\xff\xfe\x00\x01;\x81\x8d\x8f\n") in ("bad_encoding", "delimiter_undetermined")


def test_csv_limits(monkeypatch):
    monkeypatch.setattr(parse, "MAX_CELL", 10)
    assert refused(read_csv, b"a;b\n" + b"x" * 11 + b";2\n") == "cell_too_long"
    monkeypatch.setattr(parse, "MAX_CELL", 2000)
    monkeypatch.setattr(parse, "MAX_ROWS", 3)
    rows = b"a;b\n" + b"".join(b"%d;1\n" % i for i in range(60))
    assert refused(read_csv, rows) == "too_many_rows"
    monkeypatch.setattr(parse, "MAX_COLS", 2)
    assert refused(read_csv, b"a;b;c\n1;2;3\n") == "too_many_columns"


def test_csv_values_that_look_like_formulas_are_kept_as_plain_text():
    t = read_csv(b"a;b\n=HYPERLINK(\"http://evil\");@SUM(1)\n")
    assert t.rows[0][1] == ['=HYPERLINK("http://evil")', "@SUM(1)"]       # jamais interprétées ; à neutraliser à l'export


# ── XLSX ─────────────────────────────────────────────────────────────────────

def test_xlsx_values_keep_their_types():
    def build(wb):
        ws = wb.active
        ws.append(["Date", "Compte", "Montant", "Texte"])
        ws.append([datetime(2026, 1, 5), 601, 1200.5, "x"])
    t = read_xlsx(wb_bytes(build))
    assert t.headers == ["Date", "Compte", "Montant", "Texte"]
    assert t.rows[0][1][:3] == [datetime(2026, 1, 5), 601, 1200.5] and t.meta["sheet"] == "Sheet"


def test_xlsx_sheet_selection_hidden_sheets_and_errors():
    def build(wb):
        wb.active.title = "Compta"
        wb.active.append(["a", "b"])
        wb.active.append([1, 2])
        h = wb.create_sheet("Cachee")
        h.append(["x", "y"])
        h.sheet_state = "hidden"
    data = wb_bytes(build)
    assert read_xlsx(data).meta["sheet"] == "Compta"                         # la feuille masquée est ignorée
    assert refused(read_xlsx, data, "Cachee") == "unknown_sheet"

    def two(wb):
        wb.active.title = "A"
        wb.active.append(["a", "b"])
        wb.active.append([1, 2])
        s = wb.create_sheet("B")
        s.append(["a", "b"])
        s.append([3, 4])
    data2 = wb_bytes(two)
    assert refused(read_xlsx, data2) == "sheet_required"                     # plusieurs feuilles : on ne choisit pas pour l'utilisateur
    assert read_xlsx(data2, "B").rows[0][1] == [3, 4]


def test_xlsx_formulas_are_never_evaluated():
    def build(wb):
        wb.active.append(["a", "b"])
        wb.active.append([1, "=1+1"])
    t = read_xlsx(wb_bytes(build))
    assert t.rows[0][1][1] is None            # aucune valeur en cache : pas de calcul, la cellule est vide (et sera signalée)


def test_xlsx_limits_and_garbage(monkeypatch):
    def wide(wb):
        wb.active.append([f"c{i}" for i in range(5)])
        wb.active.append(list(range(5)))
    monkeypatch.setattr(parse, "MAX_COLS", 3)
    assert refused(read_xlsx, wb_bytes(wide)) == "too_many_columns"
    monkeypatch.setattr(parse, "MAX_COLS", 60)
    monkeypatch.setattr(parse, "MAX_ROWS", 2)

    def tall(wb):
        wb.active.append(["a", "b"])
        for i in range(10):
            wb.active.append([i, i])
    assert refused(read_xlsx, wb_bytes(tall)) == "too_many_rows"
    assert refused(read_xlsx, b"PK\x03\x04garbage") == "xlsx_unreadable"
    assert refused(read_xlsx, wb_bytes(lambda wb: None)) == "no_data"


def test_xlsx_with_a_bogus_huge_declared_dimension_does_not_explode():
    def build(wb):
        wb.active.append(["a", "b"])
        wb.active.append([1, 2])
    data = wb_bytes(build)
    import zipfile
    src, out = zipfile.ZipFile(io.BytesIO(data)), io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for i in src.infolist():
            raw = src.read(i.filename)
            if i.filename == "xl/worksheets/sheet1.xml":
                raw = raw.replace(b'<dimension ref="A1:B2"/>', b'<dimension ref="A1:XFD1048576"/>')
            z.writestr(i.filename, raw)
    t = read_xlsx(out.getvalue())
    assert len(t.rows) == 1 and t.rows[0][1] == [1, 2]


def test_csv_with_absurd_column_count_is_refused_before_accumulating():
    assert refused(read_csv, ("a," * 5000 + "a\n" + "1," * 5000 + "1\n").encode()) == "too_many_columns"

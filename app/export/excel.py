"""Export de résultats vers Excel (.xlsx)."""
import datetime
import io
import math
from decimal import Decimal
from typing import Any

import openpyxl
from openpyxl.styles import Font

from app.export.sanitize import neutralize_cell


def _cell(v: Any) -> Any:
    """Valeur écrite dans une cellule : nombres et dates restent typés, tout texte est neutralisé (P-082)."""
    if v is None:
        return ""
    if isinstance(v, bool | datetime.date | datetime.datetime):
        return v
    if isinstance(v, int | Decimal) or (isinstance(v, float) and math.isfinite(v)):
        return v                       # montant réel : reste un nombre exploitable
    return neutralize_cell(v if isinstance(v, str) else str(v))


def _write(ws, values: list[Any]) -> None:
    ws.append([_cell(v) for v in values])
    for c in ws[ws.max_row]:
        if isinstance(c.value, str):
            c.data_type = "s"          # jamais interprété comme formule, même si la neutralisation était contournée


def results_to_excel(
    columns: list[str], rows: list[list], title: str = "Résultats", note: str | None = None
) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = title[:31]

    # Header row
    _write(ws, list(columns))
    for cell in ws[1]:
        cell.font = Font(bold=True)

    for row in rows:
        _write(ws, list(row))

    if note:      # P-080 : provenance du chiffre (« Exploratoire, non certifié ») reprise dans l'export
        ws.append([])
        _write(ws, [note])
        ws.cell(row=ws.max_row, column=1).font = Font(italic=True)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()

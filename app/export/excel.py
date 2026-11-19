"""Export de résultats vers Excel (.xlsx)."""
import io

import openpyxl
from openpyxl.styles import Font


def results_to_excel(
    columns: list[str], rows: list[list], title: str = "Résultats", note: str | None = None
) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = title[:31]

    # Header row
    ws.append(columns)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    for row in rows:
        ws.append([(str(v) if v is not None else "") for v in row])

    if note:      # P-080 : provenance du chiffre (« Exploratoire, non certifié ») reprise dans l'export
        ws.append([])
        ws.append([note])
        ws.cell(row=ws.max_row, column=1).font = Font(italic=True)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()

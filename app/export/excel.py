"""Export de résultats vers Excel (.xlsx)."""
import io

import openpyxl
from openpyxl.styles import Font


def results_to_excel(
    columns: list[str], rows: list[list], title: str = "Résultats"
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

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()

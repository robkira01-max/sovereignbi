"""Export de résultats vers PDF avec avertissement IA (fpdf2, MIT)."""
from fpdf import FPDF

_DISCLAIMER = "Résultats générés par IA - vérifier avant usage."
_MAX_CELL_LEN = 25
_MAX_ROWS = 500


def results_to_pdf(
    columns: list[str], rows: list[list], title: str = "Résultats"
) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Title
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    if not columns:
        pdf.set_font("Helvetica", size=10)
        pdf.cell(0, 8, "Aucun résultat.", new_x="LMARGIN", new_y="NEXT")
    else:
        n_cols = max(len(columns), 1)
        col_w = min(185.0 / n_cols, 55.0)

        # Header
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_fill_color(220, 220, 220)
        for col in columns:
            pdf.cell(col_w, 7, str(col)[:_MAX_CELL_LEN], border=1, fill=True)
        pdf.ln()

        # Data rows
        pdf.set_font("Helvetica", size=7)
        for row in rows[:_MAX_ROWS]:
            for val in row:
                text = str(val)[:_MAX_CELL_LEN] if val is not None else ""
                pdf.cell(col_w, 6, text, border=1)
            pdf.ln()

    # Footer disclaimer
    pdf.set_y(-15)
    pdf.set_font("Helvetica", "I", 7)
    pdf.cell(0, 5, _DISCLAIMER, align="C")

    return bytes(pdf.output())

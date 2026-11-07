"""Export a MizanBI dashboard to a PowerPoint (.pptx) presentation.

Each tile becomes one slide:
  - KPI  → large value + title + source note
  - table → plain table (up to MAX_TABLE_ROWS rows)
  - other → title + data summary (first column, up to MAX_SUMMARY_ROWS values)

Layout: 10 × 7.5 in (standard 4:3).  Brand color comes from the
dashboard theme.  A disclaimer footer is added on every slide.
"""
from __future__ import annotations

import io
from typing import Any

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

MAX_TABLE_ROWS = 20
MAX_SUMMARY_ROWS = 10
_DISCLAIMER = "Généré par MizanBI · Données à titre indicatif · Vérification humaine requise"


# ── colour helpers ────────────────────────────────────────────────────────────

def _hex_to_rgb(hex_color: str) -> RGBColor:
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return RGBColor(0x1F, 0x77, 0xB4)
    try:
        return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    except ValueError:
        return RGBColor(0x1F, 0x77, 0xB4)


def _white() -> RGBColor:
    return RGBColor(0xFF, 0xFF, 0xFF)


def _dark() -> RGBColor:
    return RGBColor(0x22, 0x22, 0x22)


# ── slide builders ────────────────────────────────────────────────────────────

def _add_title_bar(slide, title: str, brand: RGBColor) -> None:
    left, top, width, height = Inches(0), Inches(0), Inches(10), Inches(1.0)
    bar = slide.shapes.add_shape(1, left, top, width, height)  # MSO_SHAPE_TYPE.RECTANGLE = 1
    bar.fill.solid()
    bar.fill.fore_color.rgb = brand
    bar.line.fill.background()
    tf = bar.text_frame
    tf.word_wrap = False
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    run = p.add_run()
    run.text = title
    run.font.bold = True
    run.font.size = Pt(20)
    run.font.color.rgb = _white()


def _add_disclaimer(slide) -> None:
    left, top, width, height = Inches(0), Inches(7.1), Inches(10), Inches(0.4)
    txb = slide.shapes.add_textbox(left, top, width, height)
    tf = txb.text_frame
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = _DISCLAIMER
    run.font.size = Pt(7)
    run.font.color.rgb = RGBColor(0x88, 0x88, 0x88)


def _slide_kpi(slide, tile_title: str, data: dict, brand: RGBColor) -> None:
    val = data.get("rows", [[None]])[0][0] if data.get("rows") else None
    unit = ""
    formatted = str(val) if val is not None else "—"

    # Large KPI value centred
    left, top, width, height = Inches(2), Inches(2.0), Inches(6), Inches(2.5)
    txb = slide.shapes.add_textbox(left, top, width, height)
    tf = txb.text_frame
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = formatted
    run.font.size = Pt(72)
    run.font.bold = True
    run.font.color.rgb = brand

    # Subtitle
    left2, top2, width2, height2 = Inches(2), Inches(4.5), Inches(6), Inches(0.6)
    txb2 = slide.shapes.add_textbox(left2, top2, width2, height2)
    tf2 = txb2.text_frame
    p2 = tf2.paragraphs[0]
    p2.alignment = PP_ALIGN.CENTER
    run2 = p2.add_run()
    run2.text = tile_title
    run2.font.size = Pt(16)
    run2.font.color.rgb = _dark()


def _slide_table(slide, columns: list[str], rows: list, brand: RGBColor) -> None:
    rows = rows[:MAX_TABLE_ROWS]
    if not rows or not columns:
        return
    ncols = len(columns)
    nrows = len(rows) + 1  # header

    left, top = Inches(0.5), Inches(1.2)
    width, height = Inches(9.0), Inches(5.5)
    tbl = slide.shapes.add_table(nrows, ncols, left, top, width, height).table
    tbl.first_row = True

    for ci, col in enumerate(columns):
        cell = tbl.cell(0, ci)
        cell.text = str(col)
        cell.fill.solid()
        cell.fill.fore_color.rgb = brand
        para = cell.text_frame.paragraphs[0]
        para.runs[0].font.bold = True
        para.runs[0].font.color.rgb = _white()
        para.runs[0].font.size = Pt(10)

    for ri, row in enumerate(rows, start=1):
        for ci, val in enumerate(row):
            cell = tbl.cell(ri, ci)
            cell.text = str(val) if val is not None else ""
            para = cell.text_frame.paragraphs[0]
            if para.runs:
                para.runs[0].font.size = Pt(9)


def _slide_summary(slide, tile_title: str, columns: list[str], rows: list, brand: RGBColor) -> None:
    rows = rows[:MAX_SUMMARY_ROWS]
    if not rows:
        return
    # Simple bullet list of first column values
    left, top, width, height = Inches(0.5), Inches(1.2), Inches(9.0), Inches(5.5)
    txb = slide.shapes.add_textbox(left, top, width, height)
    tf = txb.text_frame
    tf.word_wrap = True
    for i, row in enumerate(rows):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        val = row[0] if row else ""
        suffix = f"  {row[1]}" if len(row) > 1 else ""
        run = p.add_run()
        run.text = f"• {val}{suffix}"
        run.font.size = Pt(12)
        run.font.color.rgb = _dark()


# ── main entry point ──────────────────────────────────────────────────────────

def generate_pptx(dashboard: Any, store: Any) -> bytes:
    """Return the bytes of a .pptx file built from *dashboard* tiles."""
    from app.dashboards.renderer import render_tile  # lazy to avoid circular

    prs = Presentation()
    prs.slide_width = Inches(10)
    prs.slide_height = Inches(7.5)

    brand = _hex_to_rgb(dashboard.theme.primary_color)
    blank_layout = prs.slide_layouts[6]  # blank

    # Title slide
    title_slide = prs.slides.add_slide(blank_layout)
    _add_title_bar(title_slide, dashboard.title, brand)
    sub_left, sub_top, sub_w, sub_h = Inches(1), Inches(2.5), Inches(8), Inches(2)
    txb = title_slide.shapes.add_textbox(sub_left, sub_top, sub_w, sub_h)
    tf = txb.text_frame
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = dashboard.title
    run.font.size = Pt(36)
    run.font.bold = True
    run.font.color.rgb = _dark()
    _add_disclaimer(title_slide)

    for tile in dashboard.tiles:
        slide = prs.slides.add_slide(blank_layout)
        _add_title_bar(slide, tile.title, brand)
        _add_disclaimer(slide)

        try:
            result = render_tile(tile, store)
        except Exception:
            result = {"columns": [], "rows": [], "error": "Données indisponibles"}

        columns: list[str] = result.get("columns", [])
        rows: list = result.get("rows", [])

        if tile.type == "kpi":
            _slide_kpi(slide, tile.title, result, brand)
        elif tile.type == "table":
            _slide_table(slide, columns, rows, brand)
        else:
            _slide_summary(slide, tile.title, columns, rows, brand)

    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()

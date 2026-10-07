"""Sprint 23 — Universal template extractor tests."""
from __future__ import annotations

import io
import json
import tempfile
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient


# ──────────────────────────────────────────────
# Unit tests — ExtractedStructure / UniversalExtractor
# ──────────────────────────────────────────────

def test_extract_excel_numeric_columns():
    from ingestion.universal_extractor import UniversalExtractor

    df = pd.DataFrame({
        "region": ["Nord", "Sud", "Est"],
        "total_persons": [1000, 2000, 3000],
        "adults": [800, 1600, 2400],
    })
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        df.to_excel(f.name, index=False)
        path = f.name

    extractor = UniversalExtractor()
    result = extractor.extract(path, "test.xlsx")

    assert result.title == "test"
    assert len(result.kpis) >= 2
    kpi_labels = [k.label for k in result.kpis]
    assert any("total_persons" in l or "adults" in l for l in kpi_labels)
    Path(path).unlink(missing_ok=True)


def test_extract_excel_categorical_columns():
    from ingestion.universal_extractor import UniversalExtractor

    df = pd.DataFrame({
        "country": ["Ethiopia", "Somalia", "Eritrea"] * 5,
        "count": [100, 200, 300] * 5,
        "date": pd.date_range("2021-01-01", periods=15),
    })
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        df.to_excel(f.name, index=False)
        path = f.name

    result = UniversalExtractor().extract(path, "flows.xlsx")
    assert any("country" in s.content.lower() or "country" in s.title.lower()
               for s in result.sections)
    Path(path).unlink(missing_ok=True)


def test_extract_excel_date_column_produces_line_section():
    from ingestion.universal_extractor import UniversalExtractor

    df = pd.DataFrame({
        "date": pd.date_range("2021-01-01", periods=10),
        "mouvements": range(10),
    })
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        df.to_excel(f.name, index=False)
        path = f.name

    result = UniversalExtractor().extract(path, "data.xlsx")
    assert any("évolution" in s.title.lower() for s in result.sections)
    Path(path).unlink(missing_ok=True)


def test_extract_csv():
    from ingestion.universal_extractor import UniversalExtractor

    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
        df.to_csv(f.name, index=False)
        path = f.name

    result = UniversalExtractor().extract(path, "data.csv")
    assert result.title == "data"
    Path(path).unlink(missing_ok=True)


def test_extract_pdf_with_kpis():
    from ingestion.universal_extractor import UniversalExtractor
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=14)
    pdf.cell(0, 10, "OIM DJIBOUTI RAPPORT MENSUEL", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=24)
    pdf.cell(0, 12, "12182", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 10, "Mouvements observes", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, "DEMOGRAPHIE", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, "89% hommes adultes migrants economiques Ethiopie", new_x="LMARGIN", new_y="NEXT")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        pdf.output(f.name)
        path = f.name

    result = UniversalExtractor().extract(path, "report.pdf")
    assert result.title != ""
    assert len(result.kpis) >= 1
    Path(path).unlink(missing_ok=True)


def test_extract_pdf_unreadable_returns_partial():
    from ingestion.universal_extractor import UniversalExtractor

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(b"%PDF-1.4\n%%EOF")
        path = f.name

    # Should not raise, may return empty structure
    result = UniversalExtractor().extract(path, "empty.pdf")
    assert isinstance(result.title, str)
    Path(path).unlink(missing_ok=True)


def test_extract_image_with_mocked_ocr():
    from ingestion.universal_extractor import UniversalExtractor

    with patch("pytesseract.image_to_string", return_value="RAPPORT\n5 000\nPatients hospitalisés\nDÉMOGRAPHIE"):
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
            path = f.name
        with patch("PIL.Image.open", return_value=MagicMock()):
            result = UniversalExtractor().extract(path, "dash.png")
    assert result.detected_sector in ("médecine", "général", "humanitaire")
    Path(path).unlink(missing_ok=True)


def test_unsupported_extension_raises():
    from ingestion.universal_extractor import UniversalExtractor

    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        path = f.name

    with pytest.raises(ValueError, match="Format non supporté"):
        UniversalExtractor().extract(path, "doc.docx")
    Path(path).unlink(missing_ok=True)


def test_supported_extensions():
    from ingestion.universal_extractor import UniversalExtractor
    exts = UniversalExtractor.supported_extensions()
    assert ".pdf" in exts
    assert ".xlsx" in exts
    assert ".png" in exts
    assert ".jpg" in exts


# ──────────────────────────────────────────────
# Sector detection
# ──────────────────────────────────────────────

def test_detect_sector_humanitaire():
    from ingestion.universal_extractor import _detect_sector
    assert _detect_sector("flux migrant OIM UNHCR déplacement") == "humanitaire"


def test_detect_sector_finance():
    from ingestion.universal_extractor import _detect_sector
    assert _detect_sector("bilan trésorerie budget revenu OHADA") == "finance"


def test_detect_sector_medecine():
    from ingestion.universal_extractor import _detect_sector
    assert _detect_sector("patient consultation diagnostic morbidité") == "médecine"


def test_detect_sector_unknown_returns_general():
    from ingestion.universal_extractor import _detect_sector
    assert _detect_sector("rien à signaler xxx yyy zzz") == "général"


# ──────────────────────────────────────────────
# structure_to_template
# ──────────────────────────────────────────────

def test_structure_to_template_kpis_become_tiles():
    from ingestion.universal_extractor import ExtractedKPI, ExtractedSection, ExtractedStructure
    from app.templates.structure_to_template import structure_to_template

    structure = ExtractedStructure(
        title="Rapport FMP",
        kpis=[
            ExtractedKPI("12 182", "Mouvements observés"),
            ExtractedKPI("9 000", "Frontière ouest"),
        ],
        sections=[ExtractedSection("DÉMOGRAPHIE", "89% hommes")],
        detected_sector="humanitaire",
    )
    tmpl = structure_to_template(structure, user_title="FMP Djibouti")
    assert tmpl.title == "FMP Djibouti"
    assert tmpl.sector == "humanitaire"
    assert len(tmpl.tiles) >= 2
    kpi_tiles = [t for t in tmpl.tiles if t.chart_type == "kpi"]
    assert len(kpi_tiles) >= 2


def test_structure_to_template_sections_chart_types():
    from ingestion.universal_extractor import ExtractedKPI, ExtractedSection, ExtractedStructure
    from app.templates.structure_to_template import structure_to_template

    structure = ExtractedStructure(
        title="Test",
        kpis=[],
        sections=[
            ExtractedSection("DÉMOGRAPHIE", "hommes femmes"),
            ExtractedSection("NATIONALITÉS", "éthiopie"),
            ExtractedSection("VULNÉRABILITÉS", "enfants"),
            ExtractedSection("ARRIVÉES", "flux journalier"),
        ],
        detected_sector="humanitaire",
    )
    tmpl = structure_to_template(structure)
    chart_map = {t.title: t.chart_type for t in tmpl.tiles}
    assert chart_map.get("DÉMOGRAPHIE") == "bar"
    assert chart_map.get("NATIONALITÉS") == "pie"
    assert chart_map.get("VULNÉRABILITÉS") == "table"
    assert chart_map.get("ARRIVÉES") == "line"


def test_structure_to_template_max_12_tiles():
    from ingestion.universal_extractor import ExtractedKPI, ExtractedSection, ExtractedStructure
    from app.templates.structure_to_template import structure_to_template

    structure = ExtractedStructure(
        title="Big",
        kpis=[ExtractedKPI(str(i), f"KPI {i}") for i in range(20)],
        sections=[ExtractedSection(f"Section {i}", "content") for i in range(10)],
        detected_sector="général",
    )
    tmpl = structure_to_template(structure)
    assert len(tmpl.tiles) <= 12


def test_structure_to_template_empty_has_fallback_tile():
    from ingestion.universal_extractor import ExtractedStructure
    from app.templates.structure_to_template import structure_to_template

    structure = ExtractedStructure(title="Vide", detected_sector="général")
    tmpl = structure_to_template(structure)
    assert len(tmpl.tiles) >= 1


# ──────────────────────────────────────────────
# DashboardTemplate model persistence
# ──────────────────────────────────────────────

def test_save_and_load_template(tmp_path):
    from app.templates.models import DashboardTemplate, DashboardTile, save_template, load_template

    tmpl = DashboardTemplate(
        template_id=str(uuid.uuid4()),
        title="Test template",
        description="desc",
        sector="finance",
        source_format="excel",
        tiles=[DashboardTile(
            tile_id=str(uuid.uuid4()),
            title="Total ventes",
            question="Quel est le total des ventes ?",
            chart_type="kpi",
        )],
        tags=["finance"],
    )
    save_template(tmpl, base_dir=tmp_path)
    loaded = load_template(tmpl.template_id, base_dir=tmp_path)
    assert loaded.title == "Test template"
    assert len(loaded.tiles) == 1
    assert loaded.tiles[0].chart_type == "kpi"


def test_load_template_not_found_raises(tmp_path):
    from app.templates.models import load_template
    with pytest.raises(KeyError):
        load_template("nonexistent-id", base_dir=tmp_path)


def test_list_templates(tmp_path):
    from app.templates.models import DashboardTemplate, DashboardTile, save_template, list_templates

    for i in range(3):
        tmpl = DashboardTemplate(
            template_id=str(uuid.uuid4()),
            title=f"Template {i}",
            description="",
            sector="général",
            source_format="manual",
            tiles=[DashboardTile(str(uuid.uuid4()), f"Tile {i}", "Q?", "kpi")],
        )
        save_template(tmpl, base_dir=tmp_path)

    results = list_templates(base_dir=tmp_path)
    assert len(results) == 3
    assert all("tiles_count" in r for r in results)
    assert all(r["tiles_count"] == 1 for r in results)


# ──────────────────────────────────────────────
# API routes
# ──────────────────────────────────────────────

@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


EDITOR_KEY = "test-editor-key-s6"
VIEWER_KEY = "test-viewer-key-s6"
ADMIN_KEY = "test-admin-key-sprint3"


def test_extract_endpoint_excel(client):
    df = pd.DataFrame({
        "region": ["Nord", "Sud"],
        "total": [100, 200],
    })
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    buf.seek(0)

    resp = client.post(
        "/user-templates/extract",
        files={"file": ("data.xlsx", buf, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers={"X-Api-Key": EDITOR_KEY},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "structure" in data
    assert "suggested_template" in data
    assert data["suggested_template"]["tiles"]


def test_extract_endpoint_unsupported_type(client):
    resp = client.post(
        "/user-templates/extract",
        files={"file": ("doc.docx", io.BytesIO(b"fake"), "application/octet-stream")},
        headers={"X-Api-Key": EDITOR_KEY},
    )
    assert resp.status_code == 415


def test_extract_endpoint_requires_editor(client):
    buf = io.BytesIO(b"a,b\n1,2")
    resp = client.post(
        "/user-templates/extract",
        files={"file": ("data.csv", buf, "text/csv")},
        headers={"X-Api-Key": VIEWER_KEY},
    )
    assert resp.status_code == 403


def test_save_template_endpoint(client):
    payload = {
        "title": "Mon template FMP",
        "description": "OIM Djibouti",
        "sector": "humanitaire",
        "source_format": "pdf",
        "tiles": [
            {"title": "Total mouvements", "question": "Combien ?", "chart_type": "kpi", "tile_id": str(uuid.uuid4())},
            {"title": "Par nationalité", "question": "Répartition par nationalité", "chart_type": "pie", "tile_id": str(uuid.uuid4())},
        ],
        "tags": ["humanitaire", "FMP"],
    }
    resp = client.post("/user-templates/save", json=payload, headers={"X-Api-Key": EDITOR_KEY})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "template_id" in data
    assert data["tiles_count"] == 2


def test_save_template_empty_tiles_returns_400(client):
    payload = {"title": "Vide", "tiles": [], "sector": "général", "source_format": "manual"}
    resp = client.post("/user-templates/save", json=payload, headers={"X-Api-Key": EDITOR_KEY})
    assert resp.status_code == 400


def test_list_templates_endpoint(client):
    resp = client.get("/user-templates", headers={"X-Api-Key": VIEWER_KEY})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_get_template_endpoint(client):
    # Save first
    payload = {
        "title": "Readable",
        "sector": "finance",
        "source_format": "excel",
        "tiles": [{"title": "T", "question": "Q?", "chart_type": "kpi", "tile_id": str(uuid.uuid4())}],
    }
    save_resp = client.post("/user-templates/save", json=payload, headers={"X-Api-Key": EDITOR_KEY})
    tid = save_resp.json()["template_id"]

    get_resp = client.get(f"/user-templates/{tid}", headers={"X-Api-Key": VIEWER_KEY})
    assert get_resp.status_code == 200
    assert get_resp.json()["title"] == "Readable"


def test_get_template_not_found(client):
    resp = client.get("/user-templates/nonexistent-uuid", headers={"X-Api-Key": VIEWER_KEY})
    assert resp.status_code == 404


def test_apply_template_no_data_returns_400(client):
    from app.main import app  # noqa: PLC0415

    # Save a template
    payload = {
        "title": "Apply test",
        "sector": "général",
        "source_format": "manual",
        "tiles": [{"title": "Count", "question": "Combien ?", "chart_type": "kpi", "tile_id": str(uuid.uuid4())}],
    }
    save_resp = client.post("/user-templates/save", json=payload, headers={"X-Api-Key": EDITOR_KEY})
    tid = save_resp.json()["template_id"]

    # Temporarily clear store tables to guarantee no-data state
    saved_tables = set(app.state.store.tables)
    app.state.store.tables.clear()
    try:
        resp = client.post(f"/user-templates/{tid}/apply", headers={"X-Api-Key": VIEWER_KEY})
        assert resp.status_code == 400
    finally:
        app.state.store.tables.update(saved_tables)


def test_apply_template_with_data(client):
    # Upload data
    df = pd.DataFrame({"country": ["Ethiopia", "Somalia"], "count": [100, 200]})
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    buf.seek(0)
    client.post(
        "/upload",
        files={"file": ("nations.xlsx", buf, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers={"X-Api-Key": VIEWER_KEY},
    )

    # Save template
    payload = {
        "title": "Apply with data",
        "sector": "humanitaire",
        "source_format": "excel",
        "tiles": [
            {"title": "Total", "question": "Combien de lignes ?", "chart_type": "kpi", "tile_id": str(uuid.uuid4())},
            {"title": "Top pays", "question": "Répartition par pays", "chart_type": "bar", "tile_id": str(uuid.uuid4())},
        ],
    }
    save_resp = client.post("/user-templates/save", json=payload, headers={"X-Api-Key": EDITOR_KEY})
    tid = save_resp.json()["template_id"]

    apply_resp = client.post(f"/user-templates/{tid}/apply", headers={"X-Api-Key": VIEWER_KEY})
    assert apply_resp.status_code == 200
    results = apply_resp.json()
    assert len(results) == 2
    assert all("tile_id" in r for r in results)
    assert all("result" in r or "error" in r for r in results)


def test_extract_csv_endpoint(client):
    csv_content = b"name,value\nalpha,10\nbeta,20\n"
    resp = client.post(
        "/user-templates/extract",
        files={"file": ("data.csv", io.BytesIO(csv_content), "text/csv")},
        headers={"X-Api-Key": EDITOR_KEY},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["structure"]["detected_sector"] in ("général", "commerce", "finance", "humanitaire", "ingénierie", "médecine")
    assert len(data["suggested_template"]["tiles"]) >= 1

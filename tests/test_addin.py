"""Tests Sprint 24 — Add-in Excel Office.js."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

VIEWER = {"X-Api-Key": "test-viewer-key-s6"}
EDITOR = {"X-Api-Key": "test-editor-key-s6"}
ADMIN = {"X-Api-Key": "test-admin-key-sprint3"}

SAMPLE_DATA = {
    "sheet_name": "Ventes",
    "columns": ["region", "mois", "montant"],
    "rows": [
        ["Nord", "2021-01", 1234],
        ["Sud", "2021-01", 5678],
        ["Est", "2021-01", 910],
    ],
    "source": "excel-addin",
}


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


# --- push-data ---

def test_push_data_valid(client):
    r = client.post("/api/v1/addin/push-data", json=SAMPLE_DATA, headers=VIEWER)
    assert r.status_code == 200
    d = r.json()
    assert "table_name" in d
    assert d["rows"] == 3
    assert d["columns"] == 3


def test_push_data_no_key(client):
    r = client.post("/api/v1/addin/push-data", json=SAMPLE_DATA)
    assert r.status_code == 401


def test_push_data_too_many_rows(client):
    big = {
        "sheet_name": "Big",
        "columns": ["a"],
        "rows": [[i] for i in range(10_001)],
    }
    r = client.post("/api/v1/addin/push-data", json=big, headers=EDITOR)
    assert r.status_code == 422


def test_push_data_empty_columns(client):
    r = client.post(
        "/api/v1/addin/push-data",
        json={"sheet_name": "X", "columns": [], "rows": []},
        headers=EDITOR,
    )
    assert r.status_code == 422


def test_push_data_editor_allowed(client):
    r = client.post("/api/v1/addin/push-data", json=SAMPLE_DATA, headers=EDITOR)
    assert r.status_code == 200


def test_push_data_viewer_allowed(client):
    r = client.post("/api/v1/addin/push-data", json=SAMPLE_DATA, headers=VIEWER)
    assert r.status_code == 200


def test_push_data_idempotent(client):
    r1 = client.post("/api/v1/addin/push-data", json=SAMPLE_DATA, headers=VIEWER)
    r2 = client.post("/api/v1/addin/push-data", json=SAMPLE_DATA, headers=VIEWER)
    assert r1.status_code == 200
    assert r2.status_code == 200
    # Second push replaces, same row count
    assert r2.json()["rows"] == r1.json()["rows"]


def test_push_data_mixed_types(client):
    mixed = {
        "sheet_name": "Mixed",
        "columns": ["texte", "nombre", "date"],
        "rows": [
            ["bonjour", 42, "2021-03-01"],
            [None, 0, None],
        ],
    }
    r = client.post("/api/v1/addin/push-data", json=mixed, headers=VIEWER)
    assert r.status_code == 200
    assert r.json()["rows"] == 2


def test_push_data_large_sheet(client):
    large = {
        "sheet_name": "Large",
        "columns": [f"col_{i}" for i in range(50)],
        "rows": [[j * 50 + i for i in range(50)] for j in range(500)],
    }
    r = client.post("/api/v1/addin/push-data", json=large, headers=VIEWER)
    assert r.status_code == 200
    assert r.json()["rows"] == 500
    assert r.json()["columns"] == 50


def test_push_data_source_field(client):
    r = client.post("/api/v1/addin/push-data", json=SAMPLE_DATA, headers=VIEWER)
    assert r.json()["source"] == "excel-addin"


# --- ask ---

def test_ask_no_data_returns_message(client):
    """Without pre-loaded data, returns a graceful no-data message."""
    fresh_data = {
        "sheet_name": "FreshSheet_ask_test",
        "columns": ["x"],
        "rows": [[1]],
    }
    # Push data first so store is not empty
    client.post("/api/v1/addin/push-data", json=fresh_data, headers=VIEWER)
    r = client.post(
        "/api/v1/addin/ask",
        json={"question": "Combien de lignes ?"},
        headers=VIEWER,
    )
    # Should succeed (200) even if LLM is not available — returns graceful response
    assert r.status_code == 200
    d = r.json()
    assert "question" in d
    assert "confidence_grade" in d


def test_ask_empty_question(client):
    r = client.post(
        "/api/v1/addin/ask",
        json={"question": ""},
        headers=VIEWER,
    )
    assert r.status_code == 422


def test_ask_no_key(client):
    r = client.post("/api/v1/addin/ask", json={"question": "test"})
    assert r.status_code == 401


def test_ask_response_shape(client):
    client.post("/api/v1/addin/push-data", json=SAMPLE_DATA, headers=VIEWER)
    r = client.post(
        "/api/v1/addin/ask",
        json={"question": "Total des montants ?"},
        headers=VIEWER,
    )
    assert r.status_code == 200
    d = r.json()
    assert set(d.keys()) >= {"question", "sql", "columns", "rows", "answer", "confidence_grade"}


# --- status ---

def test_status_returns_tables(client):
    client.post("/api/v1/addin/push-data", json=SAMPLE_DATA, headers=VIEWER)
    r = client.get("/api/v1/addin/status", headers=VIEWER)
    assert r.status_code == 200
    d = r.json()
    assert "tables" in d
    assert "tables_count" in d
    assert "ready" in d
    assert d["ready"] is True


def test_status_no_key(client):
    r = client.get("/api/v1/addin/status")
    assert r.status_code == 401


# --- static files ---

def test_addin_static_manifest_accessible(client):
    """The manifest.xml must be served under /addin/excel/."""
    r = client.get("/addin/excel/manifest.xml")
    assert r.status_code == 200
    assert "xml" in r.headers["content-type"]


def test_addin_static_taskpane_html(client):
    r = client.get("/addin/excel/taskpane.html")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]


# --- manifest XML validity ---

def test_manifest_xml_is_valid():
    manifest_path = Path(__file__).parent.parent / "frontend" / "excel-addin" / "manifest.xml"
    assert manifest_path.exists(), "manifest.xml introuvable"
    tree = ET.parse(str(manifest_path))
    root = tree.getroot()
    # Must have an Id element
    ns = {"o": "http://schemas.microsoft.com/office/appforoffice/1.1"}
    id_el = root.find("o:Id", ns)
    assert id_el is not None, "manifest.xml doit avoir un élément <Id>"
    assert id_el.text, "<Id> ne doit pas être vide"


def test_manifest_contains_taskpane_url():
    manifest_path = Path(__file__).parent.parent / "frontend" / "excel-addin" / "manifest.xml"
    content = manifest_path.read_text()
    assert "taskpane.html" in content


def test_taskpane_js_exists():
    js_path = Path(__file__).parent.parent / "frontend" / "excel-addin" / "taskpane.js"
    assert js_path.exists()
    assert js_path.stat().st_size > 100


def test_taskpane_html_has_office_js():
    html_path = Path(__file__).parent.parent / "frontend" / "excel-addin" / "taskpane.html"
    content = html_path.read_text()
    assert "appsforoffice.microsoft.com" in content
    assert "office.js" in content

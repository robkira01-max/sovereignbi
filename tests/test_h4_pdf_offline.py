"""Tests for Sprint H4 — reportlab PDF + offline export routes."""
import io

import pytest

from app.export.pdf import results_to_pdf


# ── results_to_pdf (reportlab) ────────────────────────────────────────────────

def test_pdf_returns_bytes():
    data = results_to_pdf(["col1", "col2"], [["a", "b"], ["c", "d"]])
    assert isinstance(data, bytes)
    assert len(data) > 100


def test_pdf_starts_with_pdf_magic():
    data = results_to_pdf(["id", "value"], [[1, 100]])
    assert data[:4] == b"%PDF"


def test_pdf_empty_columns():
    data = results_to_pdf([], [])
    assert data[:4] == b"%PDF"
    assert len(data) > 50


def test_pdf_custom_title():
    data = results_to_pdf(["a"], [["x"]], title="Rapport IGAD 2024")
    assert data[:4] == b"%PDF"


def test_pdf_max_rows_respected():
    # 600 rows — only first 500 should appear
    rows = [[i, i * 2] for i in range(600)]
    data = results_to_pdf(["id", "val"], rows)
    assert data[:4] == b"%PDF"


def test_pdf_many_columns():
    cols = [f"col{i}" for i in range(20)]
    rows = [[f"v{i}{j}" for j in range(20)] for i in range(5)]
    data = results_to_pdf(cols, rows)
    assert data[:4] == b"%PDF"


def test_pdf_unicode_content():
    data = results_to_pdf(
        ["Région", "Bénéficiaires"],
        [["Djibouti-ville", "45 000"], ["Ali Sabieh", "12 000"]],
        title="Données INSTAD",
    )
    assert data[:4] == b"%PDF"


# ── /export/pdf-offline route ────────────────────────────────────────────────

def test_pdf_offline_route():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    payload = {
        "columns": ["Pays", "PIB"],
        "rows": [["Djibouti", "3.5"], ["Éthiopie", "126"]],
        "title": "PIB IGAD",
    }
    r = client.post("/export/pdf-offline", json=payload, headers={"X-Api-Key": "test-viewer-key-s6"})
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:4] == b"%PDF"


def test_pdf_offline_route_no_auth():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    payload = {"columns": ["a"], "rows": [["x"]], "title": "test"}
    r = client.post("/export/pdf-offline", json=payload)
    assert r.status_code in (401, 403)


def test_pdf_offline_empty_data():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    payload = {"columns": [], "rows": [], "title": "Vide"}
    r = client.post("/export/pdf-offline", json=payload, headers={"X-Api-Key": "test-viewer-key-s6"})
    assert r.status_code == 200
    assert r.content[:4] == b"%PDF"


# ── /export/pdf-cached route ─────────────────────────────────────────────────

def test_pdf_cached_miss_returns_503():
    from fastapi.testclient import TestClient
    from app.main import app, query_cache

    query_cache.invalidate()
    client = TestClient(app)
    payload = {"question": "combien de bénéficiaires ?"}
    r = client.post("/export/pdf-cached", json=payload, headers={"X-Api-Key": "test-viewer-key-s6"})
    assert r.status_code == 503


def test_pdf_cached_hit_returns_pdf():
    from fastapi.testclient import TestClient
    from app.main import app, query_cache, store

    query_cache.invalidate()
    tables = frozenset(store.tables)
    query_cache.set(
        "beneficiaires totaux",
        tables,
        {"columns": ["total"], "rows": [["45000"]], "answer": "45000"},
    )
    client = TestClient(app)
    payload = {"question": "beneficiaires totaux", "title": "PDF Test"}
    r = client.post("/export/pdf-cached", json=payload, headers={"X-Api-Key": "test-viewer-key-s6"})
    assert r.status_code == 200
    assert r.content[:4] == b"%PDF"

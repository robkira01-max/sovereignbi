"""Tests Marketplace Sprint 18."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.templates.catalogue import CATALOGUE_PATH, register_template
from app.templates.marketplace import (
    FEATURED_TEMPLATES,
    export_template_package,
    get_featured,
    get_trending,
    import_template_package,
    seed_featured_templates,
)

VIEWER = {"X-Api-Key": "test-viewer-key-s6"}
EDITOR = {"X-Api-Key": "test-editor-key-s6"}
ADMIN = {"X-Api-Key": "test-admin-key-sprint3"}


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def cat(tmp_path):
    return tmp_path / "catalogue.jsonl"


# --- Unit tests ---

def test_seed_featured_templates(cat):
    ids = seed_featured_templates(cat)
    assert len(ids) == len(FEATURED_TEMPLATES)
    assert "tmpl-sales-summary" in ids


def test_seed_is_idempotent(cat):
    seed_featured_templates(cat)
    ids2 = seed_featured_templates(cat)
    assert len(ids2) == len(FEATURED_TEMPLATES)


def test_get_featured(cat):
    seed_featured_templates(cat)
    featured = get_featured(cat)
    assert len(featured) == len(FEATURED_TEMPLATES)
    titles = [e.title for e in featured]
    assert "Résumé des ventes" in titles


def test_get_trending(cat):
    seed_featured_templates(cat)
    trending = get_trending(limit=3, catalogue_path=cat)
    assert len(trending) <= 3


def test_export_template_package(cat):
    register_template("t1", "Test", "desc", ["tag"], catalogue_path=cat)
    pkg = export_template_package("t1", catalogue_path=cat)
    assert pkg["format"] == "sovereignbi-template/v1"
    assert pkg["template"]["template_id"] == "t1"
    assert "exported_at" in pkg


def test_export_template_not_found(cat):
    with pytest.raises(KeyError):
        export_template_package("nonexistent", catalogue_path=cat)


def test_import_template_package(cat):
    register_template("orig", "Original", "desc", ["bi"], catalogue_path=cat)
    pkg = export_template_package("orig", catalogue_path=cat)
    imported = import_template_package(pkg, catalogue_path=cat)
    assert imported.template_id != "orig"
    assert imported.title == "Original"
    assert "bi" in imported.tags


def test_import_wrong_format(cat):
    with pytest.raises(ValueError, match="Format"):
        import_template_package({"format": "wrong/v99"}, catalogue_path=cat)


def test_search_by_tag(cat):
    seed_featured_templates(cat)
    results = seed_featured_templates(cat)
    from app.templates.catalogue import search_templates
    hits = search_templates(tags=["kpi"], catalogue_path=cat)
    assert any("kpi" in e.tags for e in hits)


# --- Route tests ---

def test_marketplace_featured_route(client):
    r = client.get("/marketplace/featured", headers=VIEWER)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert all("template_id" in e for e in data)


def test_marketplace_tags_route(client):
    r = client.get("/marketplace/tags", headers=VIEWER)
    assert r.status_code == 200
    assert isinstance(r.json()["tags"], list)


def test_marketplace_search_route(client):
    r = client.get("/marketplace/search?q=ventes", headers=VIEWER)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_marketplace_trending_route(client):
    r = client.get("/marketplace/trending?limit=3", headers=VIEWER)
    assert r.status_code == 200
    assert len(r.json()) <= 3


def test_marketplace_rate_and_export(client):
    client.post("/marketplace/seed", headers=ADMIN)
    r = client.post(
        "/marketplace/templates/tmpl-kpi-dashboard/rate",
        json={"rating": 4.5},
        headers=VIEWER,
    )
    assert r.status_code == 200
    assert r.json()["rating_count"] >= 1

    export = client.get("/marketplace/templates/tmpl-kpi-dashboard/export", headers=VIEWER)
    assert export.status_code == 200
    pkg = export.json()
    assert pkg["format"] == "sovereignbi-template/v1"


def test_marketplace_import_route(client):
    client.post("/marketplace/seed", headers=ADMIN)
    export = client.get("/marketplace/templates/tmpl-hr-headcount/export", headers=VIEWER)
    pkg = export.json()

    r = client.post("/marketplace/templates/import", json={"package": pkg}, headers=EDITOR)
    assert r.status_code == 200
    assert r.json()["title"] == pkg["template"]["title"]


def test_marketplace_export_not_found(client):
    r = client.get("/marketplace/templates/nonexistent/export", headers=VIEWER)
    assert r.status_code == 404


def test_marketplace_seed_route_admin_only(client):
    r = client.post("/marketplace/seed", headers=VIEWER)
    assert r.status_code == 403

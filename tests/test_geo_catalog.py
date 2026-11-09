"""Tests for P-022 — Catalogue géospatial centralisé MizanGeo."""
from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest
import yaml

os.environ.setdefault("SOVEREIGN_EMBEDDER", "tfidf")

VIEWER = {"X-Api-Key": "test-viewer-key-s6"}
EDITOR = {"X-Api-Key": "test-editor-key-s6"}

_CATALOG_DIR = Path(__file__).parent.parent / "data" / "geo"
_CATALOG_PATH = _CATALOG_DIR / "catalog.yaml"


# ── catalog.yaml static tests (no HTTP) ──────────────────────────────────────

def test_catalog_yaml_exists():
    assert _CATALOG_PATH.exists(), "data/geo/catalog.yaml must exist"


def test_catalog_yaml_valid():
    raw = yaml.safe_load(_CATALOG_PATH.read_text(encoding="utf-8"))
    assert raw.get("version") == "1"
    assert isinstance(raw.get("layers"), list)
    assert len(raw["layers"]) >= 3


def test_catalog_contains_adm1():
    raw = yaml.safe_load(_CATALOG_PATH.read_text(encoding="utf-8"))
    ids = {la["id"] for la in raw["layers"]}
    assert "dj_adm1" in ids


def test_catalog_contains_adm2():
    raw = yaml.safe_load(_CATALOG_PATH.read_text(encoding="utf-8"))
    ids = {la["id"] for la in raw["layers"]}
    assert "dj_adm2" in ids


def test_catalog_contains_quartiers():
    raw = yaml.safe_load(_CATALOG_PATH.read_text(encoding="utf-8"))
    ids = {la["id"] for la in raw["layers"]}
    assert "dj_quartiers" in ids


def test_all_layers_have_license():
    raw = yaml.safe_load(_CATALOG_PATH.read_text(encoding="utf-8"))
    for la in raw["layers"]:
        assert la.get("license"), f"Layer {la['id']} missing license"
        # Draft layers (e.g. user imports, pending validation) are not required
        # to have a license_url yet — only validated layers must have one.
        if la.get("status") == "validated":
            assert la.get("license_url"), f"Validated layer {la['id']} missing license_url"


def test_quartiers_has_warning():
    raw = yaml.safe_load(_CATALOG_PATH.read_text(encoding="utf-8"))
    q = next(la for la in raw["layers"] if la["id"] == "dj_quartiers")
    assert len(q.get("warnings", [])) > 0, "dj_quartiers must have quality warnings"


def test_quartiers_status_is_draft():
    raw = yaml.safe_load(_CATALOG_PATH.read_text(encoding="utf-8"))
    q = next(la for la in raw["layers"] if la["id"] == "dj_quartiers")
    assert q["status"] == "draft"


def test_adm1_adm2_status_validated():
    raw = yaml.safe_load(_CATALOG_PATH.read_text(encoding="utf-8"))
    layers_map = {la["id"]: la for la in raw["layers"]}
    assert layers_map["dj_adm1"]["status"] == "validated"
    assert layers_map["dj_adm2"]["status"] == "validated"


# ── registry unit tests ───────────────────────────────────────────────────────

def test_load_catalog_returns_all_layers():
    from app.geo_catalog.registry import load_catalog
    catalog = load_catalog()
    assert catalog.version == "1"
    assert len(catalog.layers) >= 3


def test_get_layer_known():
    from app.geo_catalog.registry import get_layer
    layer = get_layer("dj_adm1")
    assert layer is not None
    assert layer.id == "dj_adm1"
    assert layer.license == "CC BY 4.0"


def test_get_layer_unknown_returns_none():
    from app.geo_catalog.registry import get_layer
    assert get_layer("does_not_exist") is None


def test_toggle_layer_flips_enabled(tmp_path):
    """toggle_layer writes to disk and flips the flag."""
    from app.geo_catalog.registry import load_catalog, toggle_layer
    # Copy catalog to tmp
    catalog_copy = tmp_path / "catalog.yaml"
    shutil.copy(_CATALOG_PATH, catalog_copy)

    catalog = load_catalog(catalog_copy)
    original = next(la for la in catalog.layers if la.id == "dj_adm1")
    original_state = original.enabled

    updated = toggle_layer("dj_adm1", catalog_path=catalog_copy)
    assert updated is not None
    assert updated.enabled == (not original_state)

    # Verify persisted on disk
    reloaded = load_catalog(catalog_copy)
    la = next(la for la in reloaded.layers if la.id == "dj_adm1")
    assert la.enabled == (not original_state)


def test_toggle_layer_unknown_returns_none(tmp_path):
    from app.geo_catalog.registry import toggle_layer
    catalog_copy = tmp_path / "catalog.yaml"
    shutil.copy(_CATALOG_PATH, catalog_copy)
    result = toggle_layer("unknown_layer", catalog_path=catalog_copy)
    assert result is None


# ── HTTP API tests ────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


def test_list_catalog_viewer(client):
    r = client.get("/api/v1/geo/catalog", headers=VIEWER)
    assert r.status_code == 200
    data = r.json()
    assert data["version"] == "1"
    assert data["count"] >= 3
    assert isinstance(data["layers"], list)


def test_list_catalog_requires_auth(client):
    r = client.get("/api/v1/geo/catalog")
    assert r.status_code in (401, 403)


def test_list_catalog_layer_fields(client):
    r = client.get("/api/v1/geo/catalog", headers=VIEWER)
    layers = {la["id"]: la for la in r.json()["layers"]}
    la = layers["dj_adm1"]
    for field in ("id", "name_fr", "name_en", "source", "license", "license_url",
                  "api_endpoint", "enabled", "status", "warnings", "feature_count"):
        assert field in la, f"Missing field: {field}"


def test_list_catalog_enabled_only(client):
    r = client.get("/api/v1/geo/catalog?enabled_only=true", headers=VIEWER)
    assert r.status_code == 200
    for la in r.json()["layers"]:
        assert la["enabled"] is True


def test_get_layer_adm1(client):
    r = client.get("/api/v1/geo/catalog/dj_adm1", headers=VIEWER)
    assert r.status_code == 200
    la = r.json()
    assert la["id"] == "dj_adm1"
    assert la["license"] == "CC BY 4.0"


def test_get_layer_quartiers_has_warning(client):
    r = client.get("/api/v1/geo/catalog/dj_quartiers", headers=VIEWER)
    assert r.status_code == 200
    la = r.json()
    assert len(la["warnings"]) > 0
    assert la["status"] == "draft"


def test_get_layer_unknown_404(client):
    r = client.get("/api/v1/geo/catalog/does_not_exist", headers=VIEWER)
    assert r.status_code == 404


def test_toggle_requires_editor(client):
    r = client.put("/api/v1/geo/catalog/dj_adm1/toggle", headers=VIEWER)
    assert r.status_code == 403


def test_toggle_unknown_layer_404(client):
    r = client.put("/api/v1/geo/catalog/nonexistent_layer/toggle", headers=EDITOR)
    assert r.status_code == 404


def test_catalog_adm2_has_feature_count(client):
    r = client.get("/api/v1/geo/catalog/dj_adm2", headers=VIEWER)
    assert r.status_code == 200
    assert r.json()["feature_count"] == 6

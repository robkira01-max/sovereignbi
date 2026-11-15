"""P-065 : routes /semantic/validate et /semantic/resolve (authentification et contenu)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

VIEWER = {"X-Api-Key": "test-viewer-key-s6"}
EDITOR = {"X-Api-Key": "test-editor-key-s6"}


@pytest.fixture()
def client():
    from app.main import app

    with TestClient(app) as c:
        yield c
    app.state.active_sector_id = None
    app.state.active_semantic_text = None


@pytest.mark.parametrize("path", ["/semantic/validate", "/semantic/resolve?q=CA"])
def test_anonymous_rejected(client, path):
    assert client.get(path).status_code == 401


def test_validate_default_model_is_ok(client):
    r = client.get("/semantic/validate", headers=VIEWER)
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True and body["errors"] == 0 and body["sector_id"] == "default"


def test_validate_follows_the_active_sector(client):
    assert client.post("/semantic/sectors/instad_statistics/activate", headers=EDITOR).status_code == 200
    body = client.get("/semantic/validate", headers=VIEWER).json()
    assert body["sector_id"] == "instad_statistics" and body["ok"] is True


def test_resolve_returns_recognised_terms(client):
    r = client.get("/semantic/resolve", params={"q": "CA au QC pour les ventes confirmées"}, headers=VIEWER)
    assert r.status_code == 200
    kinds = {t["kind"] for t in r.json()["terms"]}
    assert {"metric", "filter", "value"} <= kinds


def test_resolve_validates_input(client):
    assert client.get("/semantic/resolve", params={"q": ""}, headers=VIEWER).status_code == 422
    assert client.get("/semantic/resolve", params={"q": "x" * 501}, headers=VIEWER).status_code == 422

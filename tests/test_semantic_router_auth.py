"""Auth + input validation on /semantic (revue de sécurité : routes autrefois publiques)."""
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


@pytest.mark.parametrize("method,path", [
    ("get", "/semantic/sectors"),
    ("get", "/semantic/sectors/active"),
    ("post", "/semantic/sectors/humanitarian/activate"),
    ("delete", "/semantic/sectors/active"),
])
def test_anonymous_rejected(client, method, path):
    assert getattr(client, method)(path).status_code == 401


def test_invalid_key_rejected(client):
    r = client.post("/semantic/sectors/humanitarian/activate", headers={"X-Api-Key": "nope"})
    assert r.status_code == 401


def test_viewer_can_read(client):
    assert client.get("/semantic/sectors", headers=VIEWER).status_code == 200
    assert client.get("/semantic/sectors/active", headers=VIEWER).status_code == 200


def test_viewer_cannot_mutate(client):
    assert client.post("/semantic/sectors/humanitarian/activate", headers=VIEWER).status_code == 403
    assert client.delete("/semantic/sectors/active", headers=VIEWER).status_code == 403
    assert client.get("/semantic/sectors/active", headers=VIEWER).json()["sector_id"] == "default"


def test_editor_can_activate_and_deactivate(client):
    r = client.post("/semantic/sectors/humanitarian/activate", headers=EDITOR)
    assert r.status_code == 200
    assert r.json()["activated"] == "humanitarian"
    assert client.get("/semantic/sectors/active", headers=VIEWER).json()["sector_id"] == "humanitarian"
    assert client.delete("/semantic/sectors/active", headers=EDITOR).status_code == 200
    assert client.get("/semantic/sectors/active", headers=VIEWER).json()["sector_id"] == "default"


def test_listing_does_not_leak_filesystem_path(client):
    sectors = client.get("/semantic/sectors", headers=VIEWER).json()["sectors"]
    assert sectors
    assert all("path" not in s for s in sectors)


def test_unknown_sector_404_without_echo(client):
    r = client.post("/semantic/sectors/nope_xyz/activate", headers=EDITOR)
    assert r.status_code == 404
    assert "nope_xyz" not in r.text


@pytest.mark.parametrize("bad", ["..", "../x", "a.b", "A_UPPER", "x" * 65, "a b", "..%2f..%2fetc"])
def test_sector_id_allowlist(bad):
    from app.semantic.sectors import load_sector, sector_exists

    assert sector_exists(bad) is False
    with pytest.raises(FileNotFoundError):
        load_sector(bad)

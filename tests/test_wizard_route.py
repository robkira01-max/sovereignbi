"""Tests routes wizard et catalogue."""
import os
import pytest
from fastapi.testclient import TestClient


_E = {"X-Api-Key": os.environ.get("SOVEREIGN_EDITOR_KEY", "test-editor-key-s6")}
_V = {"X-Api-Key": os.environ.get("SOVEREIGN_VIEWER_KEY", "test-viewer-key-s6")}


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


def test_new_session_requires_editor(client):
    r = client.post("/wizard/sessions")
    assert r.status_code == 401


def test_new_session_returns_session_id(client):
    r = client.post("/wizard/sessions", headers=_E)
    assert r.status_code == 200
    data = r.json()
    assert "session_id" in data
    assert data["step"] == "metrics"
    assert isinstance(data["available_metrics"], list)
    assert isinstance(data["available_dimensions"], list)


def test_get_session_requires_viewer(client):
    r = client.get("/wizard/sessions/nonexistent")
    assert r.status_code == 401


def test_get_session_not_found_returns_404(client):
    r = client.get("/wizard/sessions/does-not-exist-xyz", headers=_V)
    assert r.status_code == 404


def test_full_wizard_flow(client):
    # Step 1: create session
    r = client.post("/wizard/sessions", headers=_E)
    assert r.status_code == 200
    session_id = r.json()["session_id"]
    available_metrics = r.json()["available_metrics"]
    available_dimensions = r.json()["available_dimensions"]
    assert available_metrics
    assert available_dimensions

    # Step 2: select metrics
    metric_name = available_metrics[0]["name"]
    r = client.post(f"/wizard/sessions/{session_id}/metrics",
                    json={"metrics": [metric_name]}, headers=_E)
    assert r.status_code == 200
    assert r.json()["step"] == "dimensions"

    # Step 3: select dimensions
    dim_key = available_dimensions[0]["key"]
    r = client.post(f"/wizard/sessions/{session_id}/dimensions",
                    json={"dimensions": [dim_key]}, headers=_E)
    assert r.status_code == 200
    assert r.json()["step"] == "preview"

    # Step 4: generate preview
    r = client.post(f"/wizard/sessions/{session_id}/preview",
                    json={"template_name": "Test Sprint 8"}, headers=_E)
    assert r.status_code == 200
    data = r.json()
    assert len(data["generated_tiles"]) >= 1

    # Step 5: confirm
    r = client.post(f"/wizard/sessions/{session_id}/confirm", headers=_E)
    assert r.status_code == 200
    result = r.json()
    assert "template_id" in result
    assert result["tile_count"] >= 1


def test_catalogue_list_requires_viewer(client):
    r = client.get("/catalogue")
    assert r.status_code == 401


def test_catalogue_list_accessible_to_viewer(client):
    r = client.get("/catalogue", headers=_V)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_catalogue_search(client):
    r = client.get("/catalogue/search?q=ventes", headers=_V)
    assert r.status_code == 200


def test_catalogue_tags(client):
    r = client.get("/catalogue/tags", headers=_V)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

"""Tests pour l'API REST v1 (/api/v1/)."""
import io
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app, store

VIEWER = {"X-Api-Key": "test-viewer-key-s6"}
EDITOR = {"X-Api-Key": "test-editor-key-s6"}
NO_KEY = {}


@pytest.fixture
def client():
    return TestClient(app)


def test_health_v1_structure(client):
    r = client.get("/api/v1/health", headers=VIEWER)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["api_version"] == "v1"
    assert isinstance(data["tables"], list)


def test_health_v1_x_api_version_header(client):
    r = client.get("/api/v1/health", headers=VIEWER)
    assert r.headers.get("x-api-version") == "v1"


def test_health_no_auth_required(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200


def test_ask_v1_no_data_400(client):
    store.tables.clear()
    r = client.post("/api/v1/ask", json={"question": "test"}, headers=VIEWER)
    assert r.status_code == 400


def test_ask_v1_requires_viewer(client):
    r = client.post("/api/v1/ask", json={"question": "test"}, headers=NO_KEY)
    assert r.status_code == 401


def test_upload_v1_csv(client):
    csv_bytes = b"a,b\n1,2\n3,4\n"
    files = {"file": ("test.csv", io.BytesIO(csv_bytes), "text/csv")}
    r = client.post("/api/v1/upload", files=files, headers=VIEWER)
    assert r.status_code == 200
    data = r.json()
    assert "tables" in data
    assert isinstance(data["tables"], list)
    assert len(data["tables"]) >= 1


def test_upload_v1_bad_format(client):
    files = {"file": ("test.txt", io.BytesIO(b"hello"), "text/plain")}
    r = client.post("/api/v1/upload", files=files, headers=VIEWER)
    assert r.status_code == 400


def test_upload_v1_requires_viewer(client):
    files = {"file": ("test.csv", io.BytesIO(b"a\n1\n"), "text/csv")}
    r = client.post("/api/v1/upload", files=files, headers=NO_KEY)
    assert r.status_code == 401


def test_middleware_injects_version_on_old_routes(client):
    r = client.get("/health")
    assert r.headers.get("x-api-version") == "v1"


def test_openapi_schema_disabled_in_production(client):
    # /openapi.json and /docs are only served when DEBUG=true (not in prod).
    assert client.get("/openapi.json").status_code == 404
    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404


def test_openapi_schema_accessible_in_debug(client, monkeypatch):
    monkeypatch.setenv("DEBUG", "true")
    # Re-import to pick up the env var — use app.openapi() instead of the route.
    from app.main import app as _app
    schema = _app.openapi()
    assert schema["info"]["title"] == "MizanBI"
    assert schema["info"]["version"] == "1.0.0"
    paths = schema["paths"]
    assert "/api/v1/health" in paths
    assert "/api/v1/ask" in paths
    assert "/api/v1/upload" in paths

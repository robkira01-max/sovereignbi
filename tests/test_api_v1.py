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


def test_openapi_schema_accessible(client):
    r = client.get("/openapi.json")
    assert r.status_code == 200
    schema = r.json()
    assert schema["info"]["title"] == "SovereignBI"
    assert schema["info"]["version"] == "1.0.0"


def test_openapi_has_v1_paths(client):
    r = client.get("/openapi.json")
    paths = r.json()["paths"]
    assert "/api/v1/health" in paths
    assert "/api/v1/ask" in paths
    assert "/api/v1/upload" in paths


def test_docs_endpoint_accessible(client):
    r = client.get("/docs")
    assert r.status_code == 200

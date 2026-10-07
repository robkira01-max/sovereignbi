"""Tests routes embed iframe."""
import os
import pytest
from fastapi.testclient import TestClient

from app.embed.token import generate_token, EMBED_SECRET_ENV

_SECRET = "test-embed-secret-sprint8"
_A = {"X-Api-Key": os.environ.get("SOVEREIGN_ADMIN_KEY", "test-admin-key-sprint3")}
_V = {"X-Api-Key": os.environ.get("SOVEREIGN_VIEWER_KEY", "test-viewer-key-s6")}


@pytest.fixture(autouse=True)
def set_embed_secret(monkeypatch):
    monkeypatch.setenv(EMBED_SECRET_ENV, _SECRET)


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


def test_generate_embed_token_requires_admin(client):
    r = client.post("/embed/tokens", json={"dashboard_id": "*", "ttl_seconds": 3600, "scopes": ["read"]})
    assert r.status_code == 401


def test_generate_embed_token_requires_admin_not_viewer(client):
    r = client.post("/embed/tokens",
                    json={"dashboard_id": "*", "ttl_seconds": 3600, "scopes": ["read"]},
                    headers=_V)
    assert r.status_code == 403


def test_generate_embed_token_with_admin(client):
    r = client.post("/embed/tokens",
                    json={"dashboard_id": "*", "ttl_seconds": 3600, "scopes": ["read"]},
                    headers=_A)
    assert r.status_code == 200
    data = r.json()
    assert "token" in data
    assert data["dashboard_id"] == "*"


def test_embed_dashboard_with_valid_token(client, tmp_path):
    # Create a real dashboard file first
    import uuid, yaml
    from pathlib import Path
    dash_id = str(uuid.uuid4())
    dash_data = {"id": dash_id, "title": "Test", "scope": "personal",
                 "tiles": [], "theme": {}, "created_at": "", "updated_at": ""}
    dash_dir = Path("data/dashboards")
    dash_dir.mkdir(parents=True, exist_ok=True)
    (dash_dir / f"{dash_id}.yaml").write_text(yaml.safe_dump(dash_data), encoding="utf-8")

    token = generate_token(dashboard_id="*", secret=_SECRET)
    r = client.get(f"/embed/dashboard/{dash_id}?token={token.token}")
    assert r.status_code == 200
    assert r.json()["id"] == dash_id

    # cleanup
    (dash_dir / f"{dash_id}.yaml").unlink(missing_ok=True)


def test_embed_dashboard_with_expired_token(client):
    token = generate_token(dashboard_id="*", ttl_seconds=-1, secret=_SECRET)
    r = client.get(f"/embed/dashboard/any?token={token.token}")
    assert r.status_code == 401


def test_embed_dashboard_with_invalid_token(client):
    r = client.get("/embed/dashboard/any?token=not-a-real-token")
    assert r.status_code == 401


def test_embed_ask_with_invalid_token_401(client):
    r = client.get("/embed/ask?q=test&token=bad-token")
    assert r.status_code == 401


def test_embed_ask_with_valid_token_no_data(client):
    token = generate_token(dashboard_id="*", scopes=["read"], secret=_SECRET)
    r = client.get(f"/embed/ask?q=CA+total&token={token.token}")
    # No data loaded → 400
    assert r.status_code == 400

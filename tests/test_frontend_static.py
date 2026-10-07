"""Tests that FastAPI routes still work with/without the React static mount."""
import os
import pytest
from fastapi.testclient import TestClient


def test_health_still_works_with_static_mount():
    from app.main import app
    c = TestClient(app)
    r = c.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_ask_route_responds_to_bad_request():
    from app.main import app
    c = TestClient(app)
    # No data loaded + no auth key → 401
    r = c.post("/ask", json={"question": "test"})
    assert r.status_code in (401, 400)


def test_embed_route_present():
    from app.main import app
    c = TestClient(app)
    # No token → 401 or 422
    r = c.get("/embed/dashboard/fake")
    assert r.status_code in (401, 422)


def test_react_dist_absent_does_not_break_app():
    """If frontend/dist does not exist, app starts without static mount."""
    from app.main import app
    c = TestClient(app)
    r = c.get("/health")
    assert r.status_code == 200

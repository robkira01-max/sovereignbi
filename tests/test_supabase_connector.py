"""Tests du connecteur Supabase PostgREST et des routes /connectors/supabase."""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.data.supabase_connector import (
    SupabaseConnector,
    _CircuitBreaker,
    _validate_key,
    _validate_table,
    _validate_url,
)

_EDITOR_KEY = os.environ.get("SOVEREIGN_EDITOR_KEY", "test-editor-key-s6")
_E = {"X-Api-Key": _EDITOR_KEY}

_VALID_URL = "https://xyztest.supabase.co"
_VALID_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjMifQ.abc"
_OPENAPI_STUB = {
    "paths": {
        "/population": {},
        "/budget": {},
        "/meta_internal": {},
        "/_invalid__name!": {},  # doit être filtré
    }
}


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def test_validate_url_ok():
    assert _validate_url("https://abc.supabase.co/") == "https://abc.supabase.co"


def test_validate_url_rejects_http():
    with pytest.raises(ValueError, match="https://"):
        _validate_url("http://evil.internal")


def test_validate_url_rejects_non_https():
    with pytest.raises(ValueError):
        _validate_url("ftp://abc.supabase.co")


def test_validate_key_ok():
    assert _validate_key(_VALID_KEY) == _VALID_KEY


def test_validate_key_rejects_plaintext():
    with pytest.raises(ValueError, match="JWT"):
        _validate_key("not-a-jwt")


def test_validate_table_ok():
    assert _validate_table("my_table_01") == "my_table_01"


def test_validate_table_rejects_injection():
    with pytest.raises(ValueError):
        _validate_table("users; DROP TABLE users--")


def test_validate_table_rejects_spaces():
    with pytest.raises(ValueError):
        _validate_table("my table")


# ---------------------------------------------------------------------------
# Circuit breaker
# ---------------------------------------------------------------------------


def test_circuit_breaker_opens_after_max_failures():
    cb = _CircuitBreaker()
    for _ in range(3):
        cb.record_failure()
    assert cb.is_open


def test_circuit_breaker_resets_after_success():
    cb = _CircuitBreaker()
    cb.record_failure()
    cb.record_success()
    assert not cb.is_open
    assert cb.failures == 0


def test_circuit_breaker_resets_after_timeout(monkeypatch):
    import time
    cb = _CircuitBreaker()
    for _ in range(3):
        cb.record_failure()
    assert cb.is_open
    # Simuler l'expiration du cooldown
    monkeypatch.setattr(time, "monotonic", lambda: cb.open_until + 1)
    assert not cb.is_open


# ---------------------------------------------------------------------------
# SupabaseConnector unit tests (httpx mocké)
# ---------------------------------------------------------------------------


def _make_connector():
    return SupabaseConnector(url=_VALID_URL, anon_key=_VALID_KEY)


def test_connector_requires_url():
    with pytest.raises(EnvironmentError, match="URL"):
        SupabaseConnector(url="", anon_key=_VALID_KEY)


def test_connector_requires_key():
    with pytest.raises(EnvironmentError, match="manquante"):
        SupabaseConnector(url=_VALID_URL, anon_key="")


def test_list_tables_parses_openapi(monkeypatch):
    mock_resp = MagicMock()
    mock_resp.json.return_value = _OPENAPI_STUB
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.get", return_value=mock_resp):
        c = _make_connector()
        tables = c.list_tables()

    assert "population" in tables
    assert "budget" in tables
    assert "meta_internal" in tables
    assert "_invalid__name!" not in tables


def test_load_table_returns_dataframe(monkeypatch):
    rows = [{"id": 1, "nom": "Alpha"}, {"id": 2, "nom": "Beta"}]
    mock_resp = MagicMock()
    mock_resp.json.return_value = rows
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.get", return_value=mock_resp):
        c = _make_connector()
        df = c.load_table("population")

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert "nom" in df.columns


def test_load_table_rejects_bad_name():
    c = _make_connector()
    with pytest.raises(ValueError, match="invalide"):
        c.load_table("bad name!")


def test_load_table_limit_capped(monkeypatch):
    captured_params = {}

    def fake_get(url, headers=None, params=None, timeout=None):
        captured_params.update(params or {})
        mock_resp = MagicMock()
        mock_resp.json.return_value = []
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    with patch("httpx.get", side_effect=fake_get):
        c = _make_connector()
        c.load_table("population", limit=999_999)

    assert int(captured_params["limit"]) == 20_000


def test_circuit_breaker_triggers_on_http_error(monkeypatch):
    import httpx

    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = "Unauthorized"
    exc = httpx.HTTPStatusError("401", request=MagicMock(), response=mock_resp)

    with patch("httpx.get", side_effect=exc):
        c = _make_connector()
        for _ in range(3):
            try:
                c._get("/")
            except RuntimeError:
                pass

    assert c._cb.is_open


def test_circuit_breaker_blocks_subsequent_calls(monkeypatch):
    import httpx

    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.text = "error"
    exc = httpx.HTTPStatusError("500", request=MagicMock(), response=mock_resp)

    with patch("httpx.get", side_effect=exc):
        c = _make_connector()
        for _ in range(3):
            try:
                c._get("/")
            except RuntimeError:
                pass

    with pytest.raises(RuntimeError, match="circuit breaker"):
        c._get("/")


def test_test_connection_returns_true(monkeypatch):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"paths": {}}
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.get", return_value=mock_resp):
        c = _make_connector()
        assert c.test_connection() is True


def test_test_connection_returns_false_on_error(monkeypatch):
    import httpx

    mock_resp = MagicMock()
    mock_resp.status_code = 403
    mock_resp.text = "Forbidden"
    exc = httpx.HTTPStatusError("403", request=MagicMock(), response=mock_resp)

    with patch("httpx.get", side_effect=exc):
        c = _make_connector()
        assert c.test_connection() is False


# ---------------------------------------------------------------------------
# Route tests via TestClient
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    import app.main as m
    from app.data.duckdb_store import DataStore

    fresh_store = DataStore()
    original_store = m.store
    original_state = m.app.state.store
    m.store = fresh_store
    m.app.state.store = fresh_store
    yield TestClient(m.app)
    m.store = original_store
    m.app.state.store = original_state


def test_route_list_tables(client):
    with patch("app.routers.connectors.SupabaseConnector") as MockConn:
        inst = MockConn.return_value
        inst.list_tables.return_value = ["population", "budget"]
        resp = client.post(
            "/connectors/supabase/tables",
            json={"url": _VALID_URL, "anon_key": _VALID_KEY},
            headers=_E,
        )
    assert resp.status_code == 200
    assert resp.json()["tables"] == ["population", "budget"]


def test_route_load_supabase(client):
    df_data = pd.DataFrame([{"id": 1, "val": 100}, {"id": 2, "val": 200}])
    with patch("app.routers.connectors.SupabaseConnector") as MockConn:
        inst = MockConn.return_value
        inst.load_table.return_value = df_data
        resp = client.post(
            "/connectors/supabase",
            json={"table": "population", "url": _VALID_URL, "anon_key": _VALID_KEY},
            headers=_E,
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["table"] == "population"
    assert body["rows"] == 2
    assert "id" in body["columns"]


def test_route_load_supabase_empty_raises_404(client):
    with patch("app.routers.connectors.SupabaseConnector") as MockConn:
        inst = MockConn.return_value
        inst.load_table.return_value = pd.DataFrame()
        resp = client.post(
            "/connectors/supabase",
            json={"table": "empty_table", "url": _VALID_URL, "anon_key": _VALID_KEY},
            headers=_E,
        )
    assert resp.status_code == 404


def test_route_load_supabase_validation_error(client):
    with patch("app.routers.connectors.SupabaseConnector") as MockConn:
        MockConn.side_effect = ValueError("URL invalide")
        resp = client.post(
            "/connectors/supabase",
            json={"table": "t", "url": "http://bad", "anon_key": _VALID_KEY},
            headers=_E,
        )
    assert resp.status_code == 422


def test_route_load_supabase_service_error(client):
    with patch("app.routers.connectors.SupabaseConnector") as MockConn:
        inst = MockConn.return_value
        inst.load_table.side_effect = RuntimeError("circuit breaker ouvert")
        resp = client.post(
            "/connectors/supabase",
            json={"table": "t", "url": _VALID_URL, "anon_key": _VALID_KEY},
            headers=_E,
        )
    assert resp.status_code == 503


def test_route_requires_editor(client):
    resp = client.post(
        "/connectors/supabase",
        json={"table": "t", "url": _VALID_URL, "anon_key": _VALID_KEY},
        headers={"X-Api-Key": "wrong-key"},
    )
    # 401 (unauthenticated) ou 403 (mauvais rôle) sont tous deux attendus
    assert resp.status_code in (401, 403)


def test_route_appears_in_registry(client):
    df_data = pd.DataFrame([{"id": 1}])
    with patch("app.routers.connectors.SupabaseConnector") as MockConn:
        inst = MockConn.return_value
        inst.load_table.return_value = df_data
        client.post(
            "/connectors/supabase",
            json={"table": "t1", "url": _VALID_URL, "anon_key": _VALID_KEY},
            headers=_E,
        )
    viewer_key = os.environ.get("SOVEREIGN_VIEWER_KEY", "test-viewer-key-s6")
    resp = client.get("/connectors", headers={"X-Api-Key": viewer_key})
    assert resp.status_code == 200
    types = [c["type"] for c in resp.json()["connectors"]]
    assert "supabase" in types

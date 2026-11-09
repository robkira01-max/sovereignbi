"""Tests des clients KNBS et NISR et de leurs routes /connectors/."""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.data.knbs_client import (
    KNBSClient,
    KNBSDataset,
    _CircuitBreaker as KNBSCircuitBreaker,
    _safe_id,
    _safe_url,
)
from app.data.nisr_client import (
    NISRClient,
    NISRDataset,
    _CircuitBreaker as NISRCircuitBreaker,
)

_EDITOR_KEY = os.environ.get("SOVEREIGN_EDITOR_KEY", "test-editor-key-s6")
_VIEWER_KEY = os.environ.get("SOVEREIGN_VIEWER_KEY", "test-viewer-key-s6")
_E = {"X-Api-Key": _EDITOR_KEY}
_V = {"X-Api-Key": _VIEWER_KEY}

# ── Helpers ──────────────────────────────────────────────────────────────────

_CKAN_SEARCH_RESP = {
    "success": True,
    "result": {
        "results": [
            {
                "id": "abc-123",
                "name": "kenya-population-2019",
                "title": "Kenya Population Census 2019",
                "license_id": "cc-by",
                "license_title": "Creative Commons Attribution",
                "resources": [
                    {"format": "CSV", "url": "https://data.example.com/pop.csv"},
                ],
            },
            {
                "id": "def-456",
                "name": "kenya-restricted",
                "title": "Restricted Dataset",
                "license_id": "proprietaire",
                "license_title": "Proprietary",
                "resources": [],
            },
        ]
    },
}

_CKAN_SHOW_RESP = {
    "success": True,
    "result": {
        "id": "abc-123",
        "name": "kenya-population-2019",
        "title": "Kenya Population Census 2019",
        "license_id": "cc-by",
        "license_title": "Creative Commons Attribution",
        "resources": [
            {"format": "CSV", "url": "https://data.example.com/pop.csv"},
        ],
    },
}

_CKAN_SHOW_RESTRICTED = {
    "success": True,
    "result": {
        "id": "def-456",
        "name": "kenya-restricted",
        "title": "Restricted",
        "license_id": "proprietaire",
        "license_title": "Proprietary",
        "resources": [
            {"format": "CSV", "url": "https://data.example.com/restricted.csv"},
        ],
    },
}

_CSV_CONTENT = "region,population\nNairobi,4397073\nMombasa,1208333\n"

# ── Validation helpers ────────────────────────────────────────────────────────

def test_safe_url_ok():
    assert _safe_url("https://www.opendata.go.ke/api/3/action") == "https://www.opendata.go.ke/api/3/action"


def test_safe_url_rejects_http():
    with pytest.raises(ValueError, match="non-HTTPS"):
        _safe_url("http://evil.internal")


def test_safe_url_rejects_ftp():
    with pytest.raises(ValueError):
        _safe_url("ftp://host/file.csv")


def test_safe_id_ok():
    assert _safe_id("kenya-population-2019") == "kenya-population-2019"


def test_safe_id_rejects_injection():
    with pytest.raises(ValueError):
        _safe_id("id; DROP TABLE users--")


def test_safe_id_rejects_spaces():
    with pytest.raises(ValueError):
        _safe_id("bad id here")


# ── KNBSDataset licence check ─────────────────────────────────────────────────

def test_knbs_dataset_cc_by_permitted():
    ds = KNBSDataset("x", "n", "t", "cc-by", "CC-BY", [])
    assert ds.is_permitted is True


def test_knbs_dataset_proprietary_refused():
    ds = KNBSDataset("x", "n", "t", "proprietaire", "Proprietary", [])
    assert ds.is_permitted is False


def test_knbs_dataset_notspecified_permitted():
    ds = KNBSDataset("x", "n", "t", "notspecified", "", [])
    assert ds.is_permitted is True


def test_nisr_dataset_cc_by_permitted():
    ds = NISRDataset("x", "n", "t", "cc-by", "CC-BY", [])
    assert ds.is_permitted is True


def test_nisr_dataset_odc_pddl_permitted():
    ds = NISRDataset("x", "n", "t", "odc-pddl", "PDDL", [])
    assert ds.is_permitted is True


# ── Circuit breaker ───────────────────────────────────────────────────────────

def test_knbs_circuit_breaker_opens_after_3_failures():
    cb = KNBSCircuitBreaker()
    for _ in range(3):
        cb.record_failure()
    assert cb.is_open()


def test_knbs_circuit_breaker_closes_after_success():
    cb = KNBSCircuitBreaker()
    for _ in range(3):
        cb.record_failure()
    cb.record_success()
    assert not cb.is_open()


def test_nisr_circuit_breaker_opens_after_3_failures():
    cb = NISRCircuitBreaker()
    for _ in range(3):
        cb.record_failure()
    assert cb.is_open()


def test_knbs_circuit_breaker_raises_when_open():
    cb = KNBSCircuitBreaker()
    for _ in range(3):
        cb.record_failure()
    with pytest.raises(RuntimeError, match="circuit breaker"):
        cb.check()


# ── KNBSClient (mocked httpx) ─────────────────────────────────────────────────

def _mock_resp(json_data):
    m = MagicMock()
    m.json.return_value = json_data
    m.raise_for_status.return_value = None
    return m


def test_knbs_search_datasets():
    with patch("httpx.get", return_value=_mock_resp(_CKAN_SEARCH_RESP)):
        client = KNBSClient()
        results = client.search_datasets("population")
    assert len(results) == 2
    assert results[0].title == "Kenya Population Census 2019"
    assert results[0].is_permitted is True
    assert results[1].is_permitted is False


def test_knbs_get_dataset():
    with patch("httpx.get", return_value=_mock_resp(_CKAN_SHOW_RESP)):
        client = KNBSClient()
        ds = client.get_dataset("abc-123")
    assert ds.id == "abc-123"
    assert ds.license_id == "cc-by"
    assert ds.is_permitted is True


def test_knbs_fetch_csv():
    mock_csv = MagicMock()
    mock_csv.text = _CSV_CONTENT
    mock_csv.raise_for_status.return_value = None

    with patch("httpx.get", return_value=mock_csv):
        client = KNBSClient()
        df = client.fetch_csv("https://data.example.com/pop.csv")

    assert len(df) == 2
    assert "region" in df.columns
    assert df["population"].iloc[0] == 4397073


def test_knbs_fetch_csv_respects_max_rows():
    big_csv = "col\n" + "\n".join(str(i) for i in range(200))
    mock = MagicMock()
    mock.text = big_csv
    mock.raise_for_status.return_value = None

    with patch("httpx.get", return_value=mock):
        client = KNBSClient()
        df = client.fetch_csv("https://data.example.com/big.csv", max_rows=10)

    assert len(df) == 10


def test_knbs_fetch_dataset_first_csv():
    mock_show = _mock_resp(_CKAN_SHOW_RESP)
    mock_csv = MagicMock()
    mock_csv.text = _CSV_CONTENT
    mock_csv.raise_for_status.return_value = None

    with patch("httpx.get", side_effect=[mock_show, mock_csv]):
        client = KNBSClient()
        ds, df = client.fetch_dataset_first_csv("abc-123")

    assert ds.id == "abc-123"
    assert len(df) == 2


def test_knbs_fetch_dataset_raises_on_restricted_licence():
    with patch("httpx.get", return_value=_mock_resp(_CKAN_SHOW_RESTRICTED)):
        client = KNBSClient()
        with pytest.raises(PermissionError, match="proprietaire"):
            client.fetch_dataset_first_csv("def-456")


def test_knbs_fetch_dataset_raises_no_csv():
    no_csv_resp = {
        "success": True,
        "result": {
            "id": "abc-123", "name": "n", "title": "t",
            "license_id": "cc-by", "license_title": "",
            "resources": [{"format": "XLSX", "url": "https://data.example.com/file.xlsx"}],
        },
    }
    with patch("httpx.get", return_value=_mock_resp(no_csv_resp)):
        client = KNBSClient()
        with pytest.raises(ValueError, match="CSV"):
            client.fetch_dataset_first_csv("abc-123")


# ── NISRClient (mocked) ───────────────────────────────────────────────────────

_NISR_SEARCH_RESP = {
    "success": True,
    "result": {
        "results": [
            {
                "id": "rwa-001",
                "name": "rwanda-population-2022",
                "title": "Rwanda Population and Housing Census 2022",
                "license_id": "cc-by",
                "license_title": "CC-BY",
                "resources": [
                    {"format": "CSV", "url": "https://statistics.gov.rw/data/pop.csv"},
                ],
            }
        ]
    },
}

_NISR_SHOW_RESP = {
    "success": True,
    "result": {
        "id": "rwa-001",
        "name": "rwanda-population-2022",
        "title": "Rwanda Population and Housing Census 2022",
        "license_id": "cc-by",
        "license_title": "CC-BY",
        "resources": [
            {"format": "CSV", "url": "https://statistics.gov.rw/data/pop.csv"},
        ],
    },
}


def test_nisr_search_datasets():
    with patch("httpx.get", return_value=_mock_resp(_NISR_SEARCH_RESP)):
        client = NISRClient()
        results = client.search_datasets("population")
    assert len(results) == 1
    assert results[0].is_permitted is True


def test_nisr_get_dataset():
    with patch("httpx.get", return_value=_mock_resp(_NISR_SHOW_RESP)):
        client = NISRClient()
        ds = client.get_dataset("rwa-001")
    assert ds.id == "rwa-001"
    assert ds.is_permitted is True


def test_nisr_fetch_csv():
    mock = MagicMock()
    mock.text = "province,pop\nKigali,1745732\n"
    mock.raise_for_status.return_value = None

    with patch("httpx.get", return_value=mock):
        client = NISRClient()
        df = client.fetch_csv("https://statistics.gov.rw/data/pop.csv")
    assert len(df) == 1
    assert "province" in df.columns


def test_nisr_rejects_http_url():
    client = NISRClient()
    with pytest.raises(ValueError, match="non-HTTPS"):
        client.fetch_csv("http://statistics.gov.rw/data/pop.csv")


# ── API routes (FastAPI TestClient) ──────────────────────────────────────────

@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


def test_knbs_search_route(client):
    with patch("app.data.knbs_client.httpx.get", return_value=_mock_resp(_CKAN_SEARCH_RESP)):
        resp = client.post("/connectors/knbs/search", json={"q": "population"}, headers=_V)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["results"]) == 2
    assert data["results"][0]["is_permitted"] is True


def test_knbs_search_route_requires_auth(client):
    resp = client.post("/connectors/knbs/search", json={"q": "population"})
    assert resp.status_code == 401


def test_knbs_load_route(client):
    mock_show = _mock_resp(_CKAN_SHOW_RESP)
    mock_csv = MagicMock()
    mock_csv.text = _CSV_CONTENT
    mock_csv.raise_for_status.return_value = None

    with patch("app.data.knbs_client.httpx.get", side_effect=[mock_show, mock_csv]):
        resp = client.post(
            "/connectors/knbs",
            json={"dataset_id": "abc-123", "table_name": "kenya_pop"},
            headers=_E,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["table"] == "kenya_pop"
    assert data["rows"] == 2


def test_knbs_load_route_refuses_restricted(client):
    with patch("app.data.knbs_client.httpx.get", return_value=_mock_resp(_CKAN_SHOW_RESTRICTED)):
        resp = client.post(
            "/connectors/knbs",
            json={"dataset_id": "def-456"},
            headers=_E,
        )
    assert resp.status_code == 403


def test_nisr_search_route(client):
    with patch("app.data.nisr_client.httpx.get", return_value=_mock_resp(_NISR_SEARCH_RESP)):
        resp = client.post("/connectors/nisr/search", json={"q": "population"}, headers=_V)
    assert resp.status_code == 200
    data = resp.json()
    assert data["results"][0]["id"] == "rwa-001"


def test_nisr_load_route(client):
    mock_show = _mock_resp(_NISR_SHOW_RESP)
    mock_csv = MagicMock()
    mock_csv.text = "province,pop\nKigali,1745732\n"
    mock_csv.raise_for_status.return_value = None

    with patch("app.data.nisr_client.httpx.get", side_effect=[mock_show, mock_csv]):
        resp = client.post(
            "/connectors/nisr",
            json={"dataset_id": "rwa-001", "table_name": "rwanda_pop"},
            headers=_E,
        )
    assert resp.status_code == 200
    assert resp.json()["table"] == "rwanda_pop"


def test_nisr_load_route_requires_editor(client):
    resp = client.post("/connectors/nisr", json={"dataset_id": "rwa-001"}, headers=_V)
    assert resp.status_code == 403

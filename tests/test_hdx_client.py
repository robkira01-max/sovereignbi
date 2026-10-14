"""Tests for app/data/hdx_client.py — uses unittest.mock to avoid real HTTP."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from app.data.hdx_client import HdxClient, _CircuitBreaker


# ── Circuit Breaker ────────────────────────────────────────────────────────────

def test_circuit_breaker_closed_initially():
    cb = _CircuitBreaker()
    assert not cb.is_open


def test_circuit_breaker_opens_after_max_failures():
    cb = _CircuitBreaker()
    for _ in range(3):
        cb.record_failure()
    assert cb.is_open


def test_circuit_breaker_resets_after_success():
    cb = _CircuitBreaker()
    cb.record_failure()
    cb.record_failure()
    cb.record_success()
    assert not cb.is_open
    assert cb.failures == 0


def test_circuit_breaker_2_failures_not_open():
    cb = _CircuitBreaker()
    cb.record_failure()
    cb.record_failure()
    assert not cb.is_open


# ── HdxClient ────────────────────────────────────────────────────────────────

def _mock_response(json_data: dict, status_code: int = 200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    return resp


def _mock_csv_response(csv_text: str):
    resp = MagicMock()
    resp.status_code = 200
    resp.text = csv_text
    resp.raise_for_status = MagicMock()
    return resp


def test_client_default_base():
    client = HdxClient()
    assert "humdata.org" in client._base


def test_client_custom_base():
    client = HdxClient(base_url="https://example.com")
    assert client._base == "https://example.com"


def test_search_datasets_returns_list():
    payload = {
        "result": {
            "results": [
                {"name": "dataset-1", "title": "Beneficiary data"},
                {"name": "dataset-2", "title": "Displacement data"},
            ]
        }
    }
    client = HdxClient()
    with patch("httpx.get", return_value=_mock_response(payload)):
        results = client.search_datasets("beneficiary Somalia")
    assert len(results) == 2
    assert results[0]["name"] == "dataset-1"


def test_search_datasets_empty():
    payload = {"result": {"results": []}}
    client = HdxClient()
    with patch("httpx.get", return_value=_mock_response(payload)):
        results = client.search_datasets("unknown query")
    assert results == []


def test_get_resource_url_first():
    payload = {
        "result": {
            "resources": [
                {"url": "https://example.com/data.csv"},
                {"url": "https://example.com/data2.csv"},
            ]
        }
    }
    client = HdxClient()
    with patch("httpx.get", return_value=_mock_response(payload)):
        url = client.get_resource_url("dataset-abc", 0)
    assert url == "https://example.com/data.csv"


def test_get_resource_url_second():
    payload = {
        "result": {
            "resources": [
                {"url": "https://example.com/data.csv"},
                {"url": "https://example.com/data2.csv"},
            ]
        }
    }
    client = HdxClient()
    with patch("httpx.get", return_value=_mock_response(payload)):
        url = client.get_resource_url("dataset-abc", 1)
    assert url == "https://example.com/data2.csv"


def test_get_resource_url_no_resources():
    payload = {"result": {"resources": []}}
    client = HdxClient()
    with patch("httpx.get", return_value=_mock_response(payload)):
        with pytest.raises(ValueError, match="no resources"):
            client.get_resource_url("empty-dataset")


def test_get_resource_url_index_out_of_range():
    payload = {"result": {"resources": [{"url": "https://example.com/data.csv"}]}}
    client = HdxClient()
    with patch("httpx.get", return_value=_mock_response(payload)):
        with pytest.raises(IndexError):
            client.get_resource_url("dataset-abc", 5)


def test_download_csv_strips_hxl():
    csv_text = (
        "Beneficiary ID,Country,Total\n"
        "#beneficiary+id,#country+origin,#population+total\n"
        "BEN-001,Somalia,4\n"
        "BEN-002,Ethiopia,7\n"
    )
    client = HdxClient()
    with patch("httpx.get", return_value=_mock_csv_response(csv_text)):
        df = client.download_csv("https://example.com/data.csv", strip_hxl=True)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert "#beneficiary+id" not in df.values.flatten()


def test_download_csv_no_strip():
    csv_text = "ID,Name\n1,Alice\n2,Bob\n"
    client = HdxClient()
    with patch("httpx.get", return_value=_mock_csv_response(csv_text)):
        df = client.download_csv("https://example.com/data.csv", strip_hxl=False)
    assert len(df) == 2


def test_circuit_breaker_blocks_after_3_failures():
    client = HdxClient()
    with patch("httpx.get", side_effect=Exception("timeout")):
        for _ in range(3):
            try:
                client.search_datasets("test")
            except RuntimeError:
                pass
    with pytest.raises(RuntimeError, match="circuit breaker"):
        client.search_datasets("test")

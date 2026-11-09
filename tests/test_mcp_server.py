"""Tests MCP server — mock httpx, vérifie la logique de formatage."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


def _mock_get(url: str, **_):
    r = MagicMock()
    r.raise_for_status = MagicMock()
    if "/dashboards" == url.split("9001")[-1]:
        r.json.return_value = [
            {"id": "demo", "title": "Demo", "tags": ["test"], "description": "desc"},
        ]
    elif "/dashboards/demo" == url.split("9001")[-1]:
        r.json.return_value = {
            "id": "demo", "title": "Demo", "description": "desc",
            "tiles": [
                {"id": "t1", "type": "kpi", "title": "KPI",
                 "sql_pinned": "SELECT 1", "options": {"unit": "%"}},
            ],
        }
    elif "/tiles/t1/data" in url:
        r.json.return_value = {
            "columns": ["region", "valeur"],
            "rows": [["Djibouti", 42.0], ["Ali Sabieh", 23.0]],
        }
    elif "/tiles/t1/insight" in url:
        r.json.return_value = {"insight": "Le KPI est bon.", "cached": True}
    elif "/health" in url:
        r.json.return_value = {"tables": ["emploi_region", "pib_secteurs"]}
    else:
        r.json.return_value = {}
    return r


def _mock_post(url: str, **kwargs):
    r = MagicMock()
    r.raise_for_status = MagicMock()
    r.json.return_value = {
        "answer": "Le taux est de 26 %.",
        "sql": "SELECT AVG(val) FROM t",
        "data": {"columns": ["avg"], "rows": [[26.0]]},
        "confidence": "high",
    }
    return r


@pytest.fixture(autouse=True)
def _patch_httpx(monkeypatch):
    with patch("httpx.get", side_effect=_mock_get), \
         patch("httpx.post", side_effect=_mock_post):
        yield


from app.mcp.server import (
    ask,
    get_dashboard,
    get_tile_insight,
    list_dashboards,
    list_tables,
    query_tile,
)


def test_list_dashboards_contains_id():
    out = list_dashboards()
    assert "demo" in out
    assert "Demo" in out


def test_list_dashboards_shows_tags():
    out = list_dashboards()
    assert "test" in out


def test_get_dashboard_title():
    out = get_dashboard("demo")
    assert "Demo" in out


def test_get_dashboard_tile_type():
    out = get_dashboard("demo")
    assert "kpi" in out


def test_get_dashboard_sql_snippet():
    out = get_dashboard("demo")
    assert "SELECT" in out


def test_query_tile_markdown_table():
    out = query_tile("demo", "t1")
    assert "region" in out
    assert "Djibouti" in out
    assert "|" in out


def test_query_tile_row_count():
    out = query_tile("demo", "t1")
    assert "Ali Sabieh" in out


def test_get_tile_insight_text():
    out = get_tile_insight("demo", "t1")
    assert "Le KPI est bon" in out


def test_get_tile_insight_cached_suffix():
    out = get_tile_insight("demo", "t1")
    assert "cache" in out


def test_ask_contains_answer():
    out = ask("Quel est le taux ?")
    assert "26 %" in out


def test_ask_contains_sql():
    out = ask("Quel est le taux ?")
    assert "SELECT" in out


def test_ask_contains_table():
    out = ask("Quel est le taux ?")
    assert "avg" in out


def test_ask_confidence():
    out = ask("Quel est le taux ?")
    assert "high" in out


def test_ask_no_data_pipeline():
    out = ask("Bonjour ?", use_data_pipeline=False)
    assert "26 %" in out  # mock toujours retourne la même chose


def test_list_tables():
    out = list_tables()
    assert "emploi_region" in out
    assert "pib_secteurs" in out


def test_list_tables_code_format():
    out = list_tables()
    assert "`emploi_region`" in out

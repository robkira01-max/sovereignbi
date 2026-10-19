"""Tests pour le chatbot universel — /api/v1/chatbot."""
from __future__ import annotations

import io
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app, store

VIEWER = {"X-Api-Key": "test-viewer-key-s6"}
NO_KEY = {}


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def loaded_client(client):
    csv = b"region,revenue\nNord,1000\nSud,2000\n"
    client.post(
        "/api/v1/upload",
        files={"file": ("data.csv", io.BytesIO(csv), "text/csv")},
        headers=VIEWER,
    )
    return client


# --- Auth -------------------------------------------------------------------

def test_chatbot_requires_auth(client):
    r = client.post("/api/v1/chatbot", json={"question": "bonjour"}, headers=NO_KEY)
    assert r.status_code == 401


# --- Validation -------------------------------------------------------------

def test_chatbot_empty_question(client):
    r = client.post("/api/v1/chatbot", json={"question": "   "}, headers=VIEWER)
    assert r.status_code == 422


def test_chatbot_question_too_long(client):
    r = client.post(
        "/api/v1/chatbot",
        json={"question": "x" * 2001},
        headers=VIEWER,
    )
    assert r.status_code == 422


def test_chatbot_invalid_history_role(client):
    r = client.post(
        "/api/v1/chatbot",
        json={"question": "test", "history": [{"role": "system", "content": "x"}]},
        headers=VIEWER,
    )
    assert r.status_code == 422


# --- Mode général (sans données) --------------------------------------------

def test_chatbot_general_mode_no_tables(client):
    store.tables.clear()
    mock_llm = MagicMock()
    mock_llm.complete.return_value = "Bonjour ! Je suis l'assistant SovereignBI."

    with patch("app.routers.chatbot.get_llm_client", return_value=mock_llm):
        r = client.post(
            "/api/v1/chatbot",
            json={"question": "Bonjour, comment vas-tu ?"},
            headers=VIEWER,
        )

    assert r.status_code == 200
    data = r.json()
    assert data["mode"] == "general"
    assert "Bonjour" in data["answer"]
    assert data["sql"] is None
    assert data["columns"] == []


def test_chatbot_general_mode_forced(loaded_client):
    """use_data_pipeline=False force le mode général même avec des tables."""
    mock_llm = MagicMock()
    mock_llm.complete.return_value = "Réponse générale."

    with patch("app.routers.chatbot.get_llm_client", return_value=mock_llm):
        r = loaded_client.post(
            "/api/v1/chatbot",
            json={"question": "quel est le total", "use_data_pipeline": False},
            headers=VIEWER,
        )

    assert r.status_code == 200
    assert r.json()["mode"] == "general"


# --- Routage données vs général ---------------------------------------------

def test_chatbot_detects_data_question(loaded_client):
    """Question avec mot-clé data → tente le pipeline SQL."""
    mock_graph_state = {
        "sql": "SELECT sum(revenue) FROM data",
        "columns": ["sum(revenue)"],
        "rows": [(3000,)],
        "answer": "Le total des revenus est 3000.",
        "confidence": {"score": 0.9, "label": "high", "explanation": "ok"},
        "error": None,
    }
    mock_graph = MagicMock()
    mock_graph.invoke.return_value = mock_graph_state

    with patch.object(loaded_client.app.state, "get_graph", return_value=mock_graph):
        r = loaded_client.post(
            "/api/v1/chatbot",
            json={"question": "quel est le total des revenus ?"},
            headers=VIEWER,
        )

    assert r.status_code == 200
    data = r.json()
    assert data["mode"] == "data"
    assert "3000" in data["answer"]
    assert data["sql"] is not None


def test_chatbot_general_for_non_data_question(loaded_client):
    """Question générale sans mots-clés data → mode général même avec tables."""
    mock_llm = MagicMock()
    mock_llm.complete.return_value = "La BI c'est l'analyse décisionnelle."

    with patch("app.routers.chatbot.get_llm_client", return_value=mock_llm):
        r = loaded_client.post(
            "/api/v1/chatbot",
            json={"question": "qu'est-ce que la Business Intelligence ?"},
            headers=VIEWER,
        )

    assert r.status_code == 200
    assert r.json()["mode"] == "general"


# --- Historique -------------------------------------------------------------

def test_chatbot_history_passed_to_llm(client):
    store.tables.clear()
    captured = {}

    def fake_complete(system: str, user: str) -> str:
        captured["user"] = user
        return "Réponse avec historique."

    mock_llm = MagicMock()
    mock_llm.complete.side_effect = fake_complete

    history = [
        {"role": "user", "content": "Bonjour"},
        {"role": "assistant", "content": "Bonjour ! Comment puis-je aider ?"},
    ]

    with patch("app.routers.chatbot.get_llm_client", return_value=mock_llm):
        r = client.post(
            "/api/v1/chatbot",
            json={"question": "Merci", "history": history},
            headers=VIEWER,
        )

    assert r.status_code == 200
    assert "Bonjour" in captured.get("user", "")


# --- Repli gracieux ---------------------------------------------------------

def test_chatbot_pipeline_failure_fallback(loaded_client):
    """Si le pipeline SQL échoue, repli vers le mode général."""
    mock_graph = MagicMock()
    mock_graph.invoke.side_effect = RuntimeError("DuckDB error")
    mock_llm = MagicMock()
    mock_llm.complete.return_value = "Je ne peux pas calculer en ce moment."

    with (
        patch.object(loaded_client.app.state, "get_graph", return_value=mock_graph),
        patch("app.routers.chatbot.get_llm_client", return_value=mock_llm),
    ):
        r = loaded_client.post(
            "/api/v1/chatbot",
            json={"question": "quel est le total"},
            headers=VIEWER,
        )

    assert r.status_code == 200
    data = r.json()
    assert data["mode"] == "general"
    assert data["error"] is not None


# --- Schéma de réponse ------------------------------------------------------

def test_chatbot_response_schema(client):
    store.tables.clear()
    mock_llm = MagicMock()
    mock_llm.complete.return_value = "Réponse test."

    with patch("app.routers.chatbot.get_llm_client", return_value=mock_llm):
        r = client.post(
            "/api/v1/chatbot",
            json={"question": "test ?"},
            headers=VIEWER,
        )

    assert r.status_code == 200
    data = r.json()
    assert set(data.keys()) >= {"answer", "mode", "sql", "columns", "rows", "confidence", "error"}
    assert isinstance(data["columns"], list)
    assert isinstance(data["rows"], list)


# --- py_compile check (implicite via import) --------------------------------

def test_chatbot_module_importable():
    import importlib
    import app.routers.chatbot as mod
    assert hasattr(mod, "router")
    assert hasattr(mod, "ChatRequest")
    assert hasattr(mod, "ChatResponse")

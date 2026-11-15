"""Mode strict de l'IA : aucune donnée des tables du client n'est envoyée au modèle."""
from __future__ import annotations

import os

import pandas as pd
import pytest
import yaml
from fastapi.testclient import TestClient

os.environ.setdefault("SOVEREIGN_EMBEDDER", "tfidf")

from app import ai_policy  # noqa: E402
from app.data.duckdb_store import DataStore  # noqa: E402
from app.pipeline.graph import build_graph  # noqa: E402

SECRET = "SecretVilleXYZ"
VIEWER = {"X-Api-Key": "test-viewer-key-s6"}


class RecordingLLM:
    """Enregistre tous les prompts ; renvoie du SQL pour la génération et une phrase pour la réponse."""

    def __init__(self, sql="SELECT ville, taux FROM chomage"):
        self.calls: list[tuple[str, str]] = []
        self.sql = sql

    def complete(self, system, prompt):
        self.calls.append((system, prompt))
        return self.sql if "###SCHEMA###" in prompt else "Réponse rédigée par le modèle."

    @property
    def everything(self) -> str:
        return "\n".join(s + "\n" + p for s, p in self.calls)


@pytest.fixture()
def store():
    st = DataStore()
    st.load_dataframe("chomage", pd.DataFrame({"ville": [SECRET, "Autre"], "taux": [987.65, 12.5]}))
    return st


def ask(store, llm, question="chômage par ville ?", **kw):
    return build_graph(llm, store, **kw).invoke({"question": question})


# ── politique ────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("SOVEREIGN_AI_STRICT", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)


@pytest.mark.parametrize("provider,val,expected", [
    # local : inactif par défaut, activable à la main
    (None, None, False), ("ollama", "", False), ("Ollama", None, False), ("ollama", "1", True), ("ollama", " on ", True),
    ("ollama", "0", False), ("ollama", "2", False), ("ollama", "peut-être", False),
    # externe : ACTIF par défaut (même avec une valeur vide ou ambiguë), désactivable seulement explicitement
    ("kimi", None, True), ("kimi", "", True), ("KIMI", None, True), ("kimi", "1", True), ("kimi", "yes", True),
    ("kimi", "0", False), ("kimi", "false", False), ("kimi", " NO ", False), ("kimi", "off", False),
    ("kimi", "2", True), ("kimi", "peut-être", True),
    # fournisseur inconnu ou mal orthographié = externe : dans le doute, on protège
    ("kimmi", None, True), ("openai", None, True),
])
def test_strict_activation_matrix(monkeypatch, provider, val, expected):
    if provider is not None:
        monkeypatch.setenv("LLM_PROVIDER", provider)
    if val is not None:
        monkeypatch.setenv("SOVEREIGN_AI_STRICT", val)
    assert ai_policy.strict() is expected


def test_explicitly_disabled_is_only_true_for_a_clear_off_value(monkeypatch):
    assert ai_policy.explicitly_disabled() is False
    for v in ("0", "false", "No", " off "):
        monkeypatch.setenv("SOVEREIGN_AI_STRICT", v)
        assert ai_policy.explicitly_disabled() is True
    for v in ("", "1", "2", "x"):
        monkeypatch.setenv("SOVEREIGN_AI_STRICT", v)
        assert ai_policy.explicitly_disabled() is False


def test_redact_error_removes_quoted_values_and_truncates():
    e = "Conversion Error: Could not convert string 'SecretVilleXYZ' to INT32 and \"autre valeur\""
    r = ai_policy.redact_error(e)
    assert "SecretVilleXYZ" not in r and "autre valeur" not in r and "Conversion Error" in r
    assert len(ai_policy.redact_error("x" * 1000)) == 240


def test_local_answer_is_deterministic_and_data_free_of_the_model():
    assert ai_policy.local_answer(["a"], []) == "Aucun résultat pour cette question."
    assert ai_policy.local_answer(["total"], [(42,)]) == "total : 42"
    assert ai_policy.local_answer(["a", "b"], [(1, 2)]) == "1 ligne (colonnes : a, b). Consultez le tableau ci-dessous."
    assert "3 lignes" in ai_policy.local_answer(list("abcdefgh"), [(1,)] * 3) and "…" in ai_policy.local_answer(list("abcdefgh"), [(1,)] * 3)


# ── ce qui part vers le modèle ──────────────────────────────────────────────

def test_baseline_without_strict_sends_sample_rows_and_results(store, monkeypatch):
    monkeypatch.setenv("SOVEREIGN_AI_STRICT", "0")
    llm = RecordingLLM()
    ask(store, llm)
    sql_prompt, answer_prompt = llm.calls[0][1], llm.calls[1][1]
    assert SECRET in sql_prompt and "exemples" in sql_prompt          # lignes d'exemple
    assert SECRET in answer_prompt and "987.65" in answer_prompt      # lignes de résultat


def test_strict_sends_only_the_schema_and_the_question(store, monkeypatch):
    monkeypatch.setenv("SOVEREIGN_AI_STRICT", "1")
    llm = RecordingLLM()
    s = ask(store, llm, "chômage par ville ?")
    assert len(llm.calls) == 1                                         # plus d'appel pour rédiger la réponse
    sent = llm.everything
    assert SECRET not in sent and "987.65" not in sent and "exemples" not in sent
    assert "ville" in sent and "taux" in sent and "chômage par ville ?" in sent       # schéma et question restent
    assert s["answer"] == "2 lignes (colonnes : ville, taux). Consultez le tableau ci-dessous."
    assert [r[0] for r in s["rows"]] == [SECRET, "Autre"]               # l'utilisateur, lui, voit ses données


def test_strict_single_value_answer_is_local(store, monkeypatch):
    monkeypatch.setenv("SOVEREIGN_AI_STRICT", "1")
    llm = RecordingLLM("SELECT SUM(taux) AS total FROM chomage")
    s = ask(store, llm)
    assert s["answer"].startswith("total : 1000.15") or s["answer"].startswith("total : 1000.1")
    assert "1000" not in llm.everything


def test_strict_redacts_values_quoted_in_error_messages_sent_back_for_a_retry(store, monkeypatch):
    bad = "SELECT CAST(ville AS INTEGER) FROM chomage"
    monkeypatch.setenv("SOVEREIGN_AI_STRICT", "0")
    llm = RecordingLLM(bad)
    ask(store, llm)
    assert any(SECRET in p for _, p in llm.calls[1:]), "le test doit prouver que l'erreur cite bien la valeur sans mode strict"
    monkeypatch.setenv("SOVEREIGN_AI_STRICT", "1")
    llm = RecordingLLM(bad)
    ask(store, llm)
    assert len(llm.calls) >= 2 and SECRET not in llm.everything


def test_strict_withholds_document_extracts(store, monkeypatch):
    class Docs:
        chunk_count = 1
        def search(self, q, k=3): return ["c"]
        def format_context(self, chunks): return "EXTRAIT-CONFIDENTIEL-DOC"
    monkeypatch.setenv("SOVEREIGN_AI_STRICT", "0")
    llm = RecordingLLM(); ask(store, llm, doc_store=Docs())
    assert "EXTRAIT-CONFIDENTIEL-DOC" in llm.everything
    monkeypatch.setenv("SOVEREIGN_AI_STRICT", "1")
    llm = RecordingLLM(); ask(store, llm, doc_store=Docs())
    assert "EXTRAIT-CONFIDENTIEL-DOC" not in llm.everything


def test_schema_description_in_strict_has_no_values(store, monkeypatch):
    monkeypatch.setenv("SOVEREIGN_AI_STRICT", "1")
    d = store.schema_description()
    assert "Table chomage(ville VARCHAR, taux DOUBLE)" in d and SECRET not in d and "exemples" not in d
    monkeypatch.delenv("SOVEREIGN_AI_STRICT")
    monkeypatch.setenv("SOVEREIGN_AI_STRICT", "0")
    assert SECRET in store.schema_description()


# ── chat : historique ───────────────────────────────────────────────────────

def test_chat_history_keeps_only_user_turns_in_strict(monkeypatch):
    from app.routers.chatbot import Turn, _build_history_prompt
    hist = [Turn(role="user", content="Quel est le taux ?"), Turn(role="assistant", content=f"À {SECRET} il est de 987.65"),
            Turn(role="user", content="Et en 2023 ?")]
    monkeypatch.setenv("SOVEREIGN_AI_STRICT", "0")
    assert SECRET in _build_history_prompt(hist)
    monkeypatch.setenv("SOVEREIGN_AI_STRICT", "1")
    h = _build_history_prompt(hist)
    assert SECRET not in h and "Quel est le taux ?" in h and "Et en 2023 ?" in h
    assert _build_history_prompt([Turn(role="assistant", content="x")]) == ""


# ── insights ────────────────────────────────────────────────────────────────

@pytest.fixture()
def client(monkeypatch, tmp_path, store):
    from app.main import app
    monkeypatch.setattr(app.state, "store", store, raising=False)
    dd = tmp_path / "dash"; dd.mkdir()
    monkeypatch.setattr("app.routers.dashboards._DASHBOARDS_DIR", dd)
    tile = {"id": "t1", "type": "table", "title": "T", "sql_pinned": "SELECT ville, taux FROM chomage"}
    (dd / "d1.yaml").write_text(yaml.safe_dump({"id": "d1", "title": "T", "scope": "personal", "tiles": [tile],
        "theme": {"primary_color": "#1a4a8c", "font": "sans-serif", "logo_url": ""}, "created_at": "", "updated_at": ""}))
    with TestClient(app) as c:
        yield c
    app.state.active_sector_id = None
    app.state.active_semantic_text = None


def test_insight_route_is_refused_in_strict_and_never_calls_the_model(client, monkeypatch):
    called = []
    monkeypatch.setattr("app.llm.get_llm_client", lambda: called.append(1) or RecordingLLM())
    monkeypatch.setenv("SOVEREIGN_AI_STRICT", "1")
    r = client.get("/dashboards/d1/tiles/t1/insight", headers=VIEWER)
    assert r.status_code == 403 and "mode strict" in r.json()["detail"]
    assert called == []


def test_insight_cache_is_bypassed_in_strict(monkeypatch):
    from app.dashboards import insight
    monkeypatch.setenv("SOVEREIGN_AI_STRICT", "0")
    insight.set_cached("tt", "sql", "texte")
    assert insight.get_cached("tt", "sql") == "texte"
    monkeypatch.setenv("SOVEREIGN_AI_STRICT", "1")
    assert insight.get_cached("tt", "sql") is None


# ── transparence ────────────────────────────────────────────────────────────

def test_privacy_notice_reflects_strict_mode(client, monkeypatch):
    note = lambda: client.get("/compliance/notice", headers=VIEWER).json()      # noqa: E731
    monkeypatch.setenv("LLM_PROVIDER", "kimi")
    monkeypatch.setenv("SOVEREIGN_AI_STRICT", "0")                              # désactivé explicitement
    n = note()
    assert n["ai_strict_mode"] is False and "extraits de données" in n["purposes"][1]["description"]
    monkeypatch.delenv("SOVEREIGN_AI_STRICT")                                    # défaut avec un fournisseur externe : actif
    n = note()
    assert n["ai_strict_mode"] is True
    d = n["purposes"][1]["description"]
    assert "mode strict" in d and "aucune ligne de données" in d
    assert n["ai_provider"] == "kimi" and n["ai_external"] is True
    monkeypatch.setenv("LLM_PROVIDER", "ollama")                                 # local : rien n'est transmis
    n = note()
    assert n["ai_strict_mode"] is False and "local" in n["purposes"][1]["description"]
    assert n["ai_provider"] == "ollama" and n["ai_external"] is False
    monkeypatch.setenv("LLM_PROVIDER", "kimmi")                                  # faute de frappe : externe, donc protégé
    n = note()
    assert n["ai_external"] is True and n["ai_strict_mode"] is True


def test_startup_warns_only_when_strict_is_explicitly_disabled_with_an_external_llm(monkeypatch):
    from app.startup import validate_env
    monkeypatch.setenv("KIMI_BASE_URL", "https://api.example.org/v1")
    monkeypatch.setenv("KIMI_API_KEY", "k")
    has = lambda: any("SOVEREIGN_AI_STRICT" in w for w in validate_env())        # noqa: E731
    monkeypatch.setenv("LLM_PROVIDER", "kimi")
    assert has() is False                                                        # défaut : protégé, rien à signaler
    monkeypatch.setenv("SOVEREIGN_AI_STRICT", "0")
    assert has() is True                                                         # désactivé à la main : signalé
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    assert has() is False                                                        # local : pas concerné

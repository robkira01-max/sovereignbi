"""P-065 : le contexte sémantique atteint réellement le LLM (deux défauts corrigés)."""
from __future__ import annotations

import os

os.environ.setdefault("SOVEREIGN_EMBEDDER", "tfidf")

import pytest

from app.pipeline.graph import build_graph
from app.semantic.model import SemanticModel, load_model, model_to_prompt_text


class SpyLLM:
    def __init__(self):
        self.prompt = ""

    def complete(self, system, prompt):
        self.prompt = prompt
        return "SELECT 1"


class FakeStore:
    tables: set = set()

    def schema_description(self):
        return "SCHEMA"

    def execute(self, sql):
        return ["a"], [(1,)]


def run(question, **kw):
    llm = SpyLLM()
    g = build_graph(llm, FakeStore(), **kw)
    g.invoke({"question": question, "dry_run": True})
    return llm.prompt


def test_full_model_text_is_in_the_prompt():
    m = load_model()
    p = run("ventes par région", semantic=model_to_prompt_text(m), model=m)
    assert "Métriques :" in p and "Jointures :" in p and "Filtres nommés" in p


def test_resolved_terms_come_first_with_exact_definitions():
    m = load_model()
    p = run("le CA au QC pour les ventes confirmées", semantic=model_to_prompt_text(m), model=m)
    block, _, rest = p.partition("###END_SCHEMA###")
    assert "Termes reconnus" in rest.split("###QUESTION###")[0]
    assert "SUM(montant_ht)" in rest and "statut = 'confirme'" in rest and "region = 'Québec'" in rest


def test_no_resolved_block_when_nothing_matches():
    m = load_model()
    p = run("combien de lignes au total ?", semantic=model_to_prompt_text(m), model=m)
    assert "Termes reconnus" not in p


def test_semantic_model_object_is_never_printed_in_the_prompt():
    # Régression : un secteur activé passait l'objet SemanticModel, imprimé via sa repr.
    m = load_model()
    p = run("CA", semantic=m)
    assert "SemanticModel(" not in p
    assert "Métriques :" in p and "Termes reconnus" in p


def test_without_model_behaviour_is_unchanged():
    p = run("question", semantic="Règles : a")
    assert "Règles : a" in p and "Termes reconnus" not in p

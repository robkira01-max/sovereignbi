"""Tests du SchemaLinker avec TfidfEmbedder (pas de téléchargement réseau)."""
import os

import pytest

os.environ.setdefault("SOVEREIGN_EMBEDDER", "tfidf")

from app.semantic.model import load_model
from app.semantic.schema_linker import SchemaLinker, TfidfEmbedder, default_embedder


# ── fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture()
def model():
    return load_model("semantic/model.yaml")


@pytest.fixture()
def linker(model):
    emb = TfidfEmbedder()
    lk = SchemaLinker(model, emb, top_k=6)
    lk.index()
    return lk


# ── TfidfEmbedder ────────────────────────────────────────────────────────────

def test_tfidf_embed_shape():
    emb = TfidfEmbedder()
    emb.fit(["chiffre d'affaires", "marge brute", "panier moyen"])
    vecs = emb.embed(["chiffre d'affaires"])
    assert len(vecs) == 1
    assert len(vecs[0]) > 0


def test_tfidf_embed_without_prior_fit():
    emb = TfidfEmbedder()
    vecs = emb.embed(["test auto fit"])
    assert len(vecs) == 1


def test_tfidf_returns_floats():
    emb = TfidfEmbedder()
    emb.fit(["hello", "world"])
    vecs = emb.embed(["hello"])
    assert all(isinstance(v, float) for v in vecs[0])


# ── default_embedder ─────────────────────────────────────────────────────────

def test_default_embedder_tfidf(monkeypatch):
    monkeypatch.setenv("SOVEREIGN_EMBEDDER", "tfidf")
    emb = default_embedder()
    assert isinstance(emb, TfidfEmbedder)


# ── SchemaLinker.index ────────────────────────────────────────────────────────

def test_index_populates_items(linker):
    assert len(linker._items) > 0


def test_index_has_column_entries(linker):
    col_entries = [it for it in linker._items if it.get("col")]
    assert len(col_entries) > 0


def test_index_has_metric_entries(linker):
    met_entries = [it for it in linker._items if it.get("metric")]
    assert len(met_entries) > 0


def test_index_creates_qdrant_collection(linker):
    assert linker._qdrant().collection_exists("schema_items")


def test_reindex_replaces_collection(model):
    emb = TfidfEmbedder()
    lk = SchemaLinker(model, emb, top_k=4)
    lk.index()
    lk.index()  # second call must not raise
    assert len(lk._items) > 0


# ── SchemaLinker.get_relevant_context ────────────────────────────────────────

def test_context_not_empty(linker):
    ctx = linker.get_relevant_context("Quel est le chiffre d'affaires du mois ?")
    assert len(ctx) > 0


def test_context_contains_table_section(linker):
    ctx = linker.get_relevant_context("Liste les ventes par région")
    assert "ventes_detail" in ctx or "Tables" in ctx


def test_context_contains_metric_for_ca(linker):
    ctx = linker.get_relevant_context("chiffre d'affaires total cette année")
    assert "SUM(montant_ht)" in ctx or "chiffre" in ctx.lower()


def test_context_contains_rules(linker):
    ctx = linker.get_relevant_context("Quel est le montant moyen d'une commande ?")
    assert "Règles" in ctx or "CAD" in ctx


def test_context_join_for_marge(linker):
    ctx = linker.get_relevant_context("Calculer la marge brute par produit")
    # marge brute needs a join — jointure should appear
    assert "produits" in ctx or "ventes_detail" in ctx


def test_context_empty_model():
    from app.semantic.model import SemanticModel
    m = SemanticModel(schema_version="1")
    emb = TfidfEmbedder()
    lk = SchemaLinker(m, emb)
    ctx = lk.get_relevant_context("Question quelconque")
    assert ctx == ""


def test_context_auto_indexes_on_first_call(model):
    emb = TfidfEmbedder()
    lk = SchemaLinker(model, emb, top_k=4)
    # Do NOT call lk.index() explicitly
    ctx = lk.get_relevant_context("Nombre de commandes ?")
    assert len(ctx) > 0

"""P-065 : résolution déterministe des termes métier (mesures, filtres, colonnes, valeurs)."""
from __future__ import annotations

import pytest

from app.semantic.model import (
    ColumnInfo, FilterInfo, MetricInfo, SemanticModel, TableInfo, ValueSynonym, load_model, model_to_prompt_text,
)
from app.semantic.resolver import format_resolved, normalize, resolve_terms


@pytest.fixture()
def model() -> SemanticModel:
    return SemanticModel(
        schema_version="2",
        tables=[TableInfo("ventes", "", [ColumnInfo("region", "varchar", "", ["province de la vente"]),
                                         ColumnInfo("statut", "varchar", "")])],
        metrics=[
            MetricInfo("chiffre d'affaires", ["CA", "revenu"], "SUM(montant_ht)", ["ventes"], "Somme HT", unit="CAD"),
            MetricInfo("marge brute", ["marge"], "SUM(m)", ["ventes"]),
        ],
        filters=[FilterInfo("ventes confirmées", "statut = 'confirme'", ["commandes confirmées"], ["ventes"])],
        value_synonyms=[ValueSynonym("ventes", "region", "Québec", ["QC", "Quebec"])],
    )


def targets(model, q):
    return [(t.kind, t.target) for t in resolve_terms(model, q)]


def test_normalize_ignores_case_accents_apostrophes_and_plural():
    assert normalize("Chiffre d’affaires") == normalize("chiffre d'affaires") == normalize("CHIFFRE D AFFAIRES")
    assert normalize("Ventes Confirmées") == normalize("vente confirmee")


def test_metric_found_by_name_alias_and_any_spelling(model):
    for q in ("Quel est le chiffre d'affaires ?", "le CA du mois", "Revenus par mois", "CHIFFRE D’AFFAIRES"):
        assert ("metric", "chiffre d'affaires") in targets(model, q), q


def test_short_alias_is_case_exact_so_french_ca_with_cedilla_is_ignored(model):
    assert targets(model, "ça va bien") == []
    assert targets(model, "ca va bien") == []          # « ca » minuscule : pas le synonyme « CA »
    assert targets(model, "Quel CA ?") == [("metric", "chiffre d'affaires")]


def test_longest_match_wins_without_overlap(model):
    # « marge brute » ne doit pas aussi déclencher « marge »
    assert targets(model, "la marge brute par région") == [("metric", "marge brute")]


def test_filters_columns_and_values(model):
    got = targets(model, "ventes confirmées au QC par province de la vente")
    assert ("filter", "ventes confirmées") in got
    assert ("value", "ventes.region") in got
    assert ("column", "ventes.region") in got


def test_value_synonym_gives_canonical_value(model):
    t = resolve_terms(model, "ventes au Quebec")[0]
    assert t.definition == "ventes.region = 'Québec'"


def test_same_object_is_listed_once(model):
    assert len(resolve_terms(model, "CA, revenu, chiffre d'affaires")) == 1


def test_order_of_appearance(model):
    kinds = [t.kind for t in resolve_terms(model, "QC puis le CA des ventes confirmées")]
    assert kinds == ["value", "metric", "filter"]


def test_empty_inputs_are_safe(model):
    assert resolve_terms(None, "x") == []
    assert resolve_terms(model, "") == []
    assert resolve_terms(SemanticModel("2"), "chiffre d'affaires") == []
    assert format_resolved([]) == ""


def test_format_contains_exact_definitions_and_unit(model):
    txt = format_resolved(resolve_terms(model, "CA des ventes confirmées au QC"))
    assert "SUM(montant_ht)" in txt and "CAD" in txt
    assert "statut = 'confirme'" in txt
    assert "region = 'Québec'" in txt
    assert txt.startswith("Termes reconnus")


def test_default_model_resolves_a_real_question():
    m = load_model()
    got = targets(m, "Quel est le CA au QC pour les ventes confirmées ?")
    assert ("metric", "chiffre d'affaires") in got and ("filter", "ventes confirmées") in got
    assert any(k == "value" for k, _ in got)


def test_prompt_text_lists_filters_synonyms_and_units():
    txt = model_to_prompt_text(load_model())
    assert "Filtres nommés" in txt and "statut = 'confirme'" in txt
    assert "Synonymes de valeurs" in txt and "QC" in txt
    assert "[CAD]" in txt

"""P-065 : validation du modèle sémantique."""
from __future__ import annotations

from app.semantic.model import (
    ColumnInfo, FilterInfo, MetricInfo, SemanticModel, TableInfo, ValueSynonym, load_model,
)
from app.semantic.sectors import list_sectors, load_sector
from app.semantic.validate import validate_model


def base() -> SemanticModel:
    return SemanticModel(
        schema_version="2",
        tables=[TableInfo("ventes", "", [ColumnInfo("montant", "float", ""), ColumnInfo("statut", "varchar", ""),
                                         ColumnInfo("region", "varchar", "")])],
        metrics=[MetricInfo("total", ["somme"], "SUM(montant)", ["ventes"], "Somme")],
        filters=[FilterInfo("confirmées", "statut = 'ok'", [], ["ventes"])],
        value_synonyms=[ValueSynonym("ventes", "region", "Québec", ["QC"])],
    )


def codes(m):
    return {(i.level, i.code) for i in validate_model(m)}


def test_clean_model_has_no_issue():
    assert validate_model(base()) == []


def test_default_and_all_sector_models_have_no_error():
    models = [load_model()] + [load_sector(s["id"]) for s in list_sectors()]
    for m in models:
        assert [i for i in validate_model(m) if i.level == "error"] == []


def test_unparseable_sql_is_an_error():
    m = base(); m.metrics[0].sql = "SUM(montant"
    assert ("error", "bad_sql") in codes(m)


def test_unknown_column_and_table():
    m = base(); m.metrics[0].sql = "SUM(inconnue)"
    assert ("error", "unknown_column") in codes(m)
    m = base(); m.metrics[0].tables = ["absente"]
    assert ("error", "unknown_table") in codes(m)


def test_column_known_elsewhere_but_not_declared_is_a_warning():
    m = base(); m.tables.append(TableInfo("autre", "", [ColumnInfo("poids", "float", "")]))
    m.metrics[0].sql = "SUM(poids)"
    assert ("warning", "column_outside_tables") in codes(m)


def test_qualified_column_is_checked_against_the_whole_model():
    m = base(); m.metrics[0].sql = "SUM(v.montant)"
    assert validate_model(m) == []
    m.metrics[0].sql = "SUM(v.fantome)"
    assert ("error", "unknown_column") in codes(m)


def test_duplicate_names_ignore_case_and_accents():
    m = base(); m.metrics.append(MetricInfo("TOTAL", [], "COUNT(*)", ["ventes"], "x"))
    assert ("error", "duplicate_name") in codes(m)


def test_ambiguous_alias_between_two_objects():
    m = base(); m.filters[0].aliases = ["somme"]       # « somme » est déjà un alias de la mesure « total »
    assert ("error", "ambiguous_alias") in codes(m)


def test_value_synonym_must_point_to_an_existing_column():
    m = base(); m.value_synonyms[0].column = "nope"
    assert ("error", "unknown_column") in codes(m)
    m = base(); m.value_synonyms[0].table = "nope"
    assert ("error", "unknown_table") in codes(m)


def test_missing_description_is_only_a_warning():
    m = base(); m.metrics[0].description = ""
    assert codes(m) == {("warning", "no_description")}

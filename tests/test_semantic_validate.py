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


# ── P-066 : métadonnées d'indicateur ──────────────────────────────────────────

def indicator() -> SemanticModel:
    m = base()
    m.metrics[0].code = "TOTAL_VENTES"
    m.metrics[0].source = "Service X"
    m.metrics[0].frequency = "M"
    m.metrics[0].last_updated = "2026-11-15"
    return m


def test_valid_indicator_metadata_has_no_issue():
    assert validate_model(indicator()) == []


def test_indicator_code_format_and_uniqueness():
    m = indicator(); m.metrics[0].code = "total ventes"
    assert ("error", "bad_indicator_code") in codes(m)
    m = indicator(); m.metrics.append(MetricInfo("autre", [], "SUM(montant)", ["ventes"], "x", code="TOTAL_VENTES"))
    assert ("error", "duplicate_indicator_code") in codes(m)


def test_frequency_must_be_an_sdmx_code_and_date_iso():
    m = indicator(); m.metrics[0].frequency = "mensuel"
    assert ("error", "bad_frequency") in codes(m)
    m = indicator(); m.metrics[0].last_updated = "15/11/2026"
    assert ("error", "bad_date") in codes(m)


def test_indicator_without_source_or_definition_is_a_warning():
    m = indicator(); m.metrics[0].source = ""; m.metrics[0].description = ""
    assert {("warning", "indicator_without_source"), ("warning", "indicator_without_definition")} <= codes(m)


# ── P-073 : mesure liée à une formule du registre financier ─────────────────

def test_metric_formula_must_exist_in_registry():
    m = base()
    m.metrics[0].formula = "BUD001"
    assert validate_model(m) == []                                  # formule livrée : valide
    m.metrics[0].formula = "NOPE999"
    assert ("error", "unknown_formula") in codes(m)


def test_metric_formula_defaults_to_empty_and_loads_from_yaml(tmp_path):
    p = tmp_path / "m.yaml"
    p.write_text("schema_version: '2'\ntables: []\nmetrics:\n  - {name: taux, sql: 'SUM(1)', tables: [], formula: REC001}\n"
                 "  - {name: autre, sql: 'SUM(1)', tables: []}\n")
    m = load_model(p)
    assert [x.formula for x in m.metrics] == ["REC001", ""]


def test_broken_registry_is_reported_not_ignored(tmp_path, monkeypatch):
    monkeypatch.setenv("SOVEREIGN_FORMULAS_DIR", str(tmp_path / "absent"))
    m = base()
    m.metrics[0].formula = "BUD001"
    assert ("error", "formula_registry_unavailable") in codes(m)

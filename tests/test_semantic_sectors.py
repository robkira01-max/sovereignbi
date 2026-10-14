"""Tests for app/semantic/sectors.py and the three sector YAML files."""
import pytest
from pathlib import Path


def test_sectors_dir_exists():
    assert Path("semantic/sectors").exists()


def test_list_sectors_returns_list():
    from app.semantic.sectors import list_sectors
    sectors = list_sectors()
    assert isinstance(sectors, list)
    assert len(sectors) >= 3


def test_list_sectors_has_required_fields():
    from app.semantic.sectors import list_sectors
    for s in list_sectors():
        assert "id" in s
        assert "label" in s
        assert "description" in s


def test_sector_exists_humanitarian():
    from app.semantic.sectors import sector_exists
    assert sector_exists("humanitarian")


def test_sector_exists_igad():
    from app.semantic.sectors import sector_exists
    assert sector_exists("igad_economic")


def test_sector_exists_instad():
    from app.semantic.sectors import sector_exists
    assert sector_exists("instad_census")


def test_sector_not_exists():
    from app.semantic.sectors import sector_exists
    assert not sector_exists("nonexistent_sector_xyz")


def test_load_sector_humanitarian():
    from app.semantic.sectors import load_sector
    model = load_sector("humanitarian")
    assert model is not None
    assert len(model.tables) >= 4
    assert len(model.metrics) >= 5


def test_load_sector_igad():
    from app.semantic.sectors import load_sector
    model = load_sector("igad_economic")
    assert len(model.tables) >= 4
    assert len(model.metrics) >= 4


def test_load_sector_instad():
    from app.semantic.sectors import load_sector
    model = load_sector("instad_census")
    assert len(model.tables) >= 3
    assert len(model.metrics) >= 4


def test_load_sector_not_found():
    from app.semantic.sectors import load_sector
    with pytest.raises(FileNotFoundError):
        load_sector("does_not_exist_abc")


def test_humanitarian_has_beneficiaires_table():
    from app.semantic.sectors import load_sector
    model = load_sector("humanitarian")
    names = [t.name for t in model.tables]
    assert "beneficiaires" in names


def test_humanitarian_has_distributions_table():
    from app.semantic.sectors import load_sector
    model = load_sector("humanitarian")
    names = [t.name for t in model.tables]
    assert "distributions" in names


def test_humanitarian_metric_aliases_multilingual():
    from app.semantic.sectors import load_sector
    model = load_sector("humanitarian")
    metric = next(m for m in model.metrics if m.name == "total_beneficiaires")
    aliases_joined = " ".join(metric.aliases)
    # Must have Arabic alias
    assert any("؀" <= c <= "ۿ" for c in aliases_joined), "No Arabic alias found"
    # Must have English alias
    assert "beneficiar" in aliases_joined.lower()


def test_igad_has_securite_alimentaire_table():
    from app.semantic.sectors import load_sector
    model = load_sector("igad_economic")
    names = [t.name for t in model.tables]
    assert "securite_alimentaire" in names


def test_instad_has_population_region_table():
    from app.semantic.sectors import load_sector
    model = load_sector("instad_census")
    names = [t.name for t in model.tables]
    assert "population_region" in names


def test_sector_model_has_rules():
    from app.semantic.sectors import load_sector
    model = load_sector("humanitarian")
    assert len(model.rules) >= 3


def test_sector_model_has_glossary():
    from app.semantic.sectors import load_sector
    model = load_sector("humanitarian")
    assert len(model.glossary) >= 3

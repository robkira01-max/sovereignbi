"""Tests for Sprint H3 sector dashboard templates."""
from app.templates.sectors import ALL_SECTOR_TEMPLATES
from app.templates.sectors.humanitarian import HUMANITARIAN_TEMPLATES
from app.templates.sectors.igad import IGAD_TEMPLATES


def test_all_sector_templates_non_empty():
    assert len(ALL_SECTOR_TEMPLATES) > 0


def test_humanitarian_templates_count():
    assert len(HUMANITARIAN_TEMPLATES) >= 3


def test_igad_templates_count():
    assert len(IGAD_TEMPLATES) >= 3


def test_all_templates_have_required_fields():
    for tmpl in ALL_SECTOR_TEMPLATES:
        assert "template_id" in tmpl, f"Missing template_id: {tmpl}"
        assert "title" in tmpl, f"Missing title: {tmpl}"
        assert "description" in tmpl, f"Missing description: {tmpl}"
        assert "tags" in tmpl, f"Missing tags: {tmpl}"
        assert "sector" in tmpl, f"Missing sector: {tmpl}"
        assert "tiles" in tmpl, f"Missing tiles: {tmpl}"


def test_all_template_ids_unique():
    ids = [t["template_id"] for t in ALL_SECTOR_TEMPLATES]
    assert len(ids) == len(set(ids)), "Duplicate template IDs found"


def test_humanitarian_sector_field():
    for tmpl in HUMANITARIAN_TEMPLATES:
        assert tmpl["sector"] == "humanitarian"


def test_igad_sector_field():
    for tmpl in IGAD_TEMPLATES:
        assert tmpl["sector"] == "igad_economic"


def test_humanitarian_beneficiaries_template_exists():
    ids = [t["template_id"] for t in HUMANITARIAN_TEMPLATES]
    assert "tmpl-hum-beneficiaries" in ids


def test_humanitarian_distributions_template_exists():
    ids = [t["template_id"] for t in HUMANITARIAN_TEMPLATES]
    assert "tmpl-hum-distributions" in ids


def test_igad_economy_template_exists():
    ids = [t["template_id"] for t in IGAD_TEMPLATES]
    assert "tmpl-igad-economy" in ids


def test_igad_food_security_template_exists():
    ids = [t["template_id"] for t in IGAD_TEMPLATES]
    assert "tmpl-igad-food-security" in ids


def test_humanitarian_tiles_have_type():
    for tmpl in HUMANITARIAN_TEMPLATES:
        for tile in tmpl["tiles"]:
            assert "type" in tile, f"Tile missing 'type' in {tmpl['template_id']}"
            assert tile["type"] in ("kpi", "bar", "line", "table")


def test_igad_tiles_have_type():
    for tmpl in IGAD_TEMPLATES:
        for tile in tmpl["tiles"]:
            assert "type" in tile
            assert tile["type"] in ("kpi", "bar", "line", "table")


def test_all_templates_tags_are_lists():
    for tmpl in ALL_SECTOR_TEMPLATES:
        assert isinstance(tmpl["tags"], list)


def test_combined_count():
    assert len(ALL_SECTOR_TEMPLATES) == len(HUMANITARIAN_TEMPLATES) + len(IGAD_TEMPLATES)

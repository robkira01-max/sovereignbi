"""Tests du catalogue de templates."""
import pytest
from app.templates.catalogue import (
    register_template,
    rate_template,
    search_templates,
    clone_template,
    get_entry,
    list_entries,
    list_tags,
)
from app.dashboards.models import DashboardTemplate, DashboardTheme, Tile, save_template


def _make_template(templates_dir, title="Test") -> str:
    import uuid
    tid = str(uuid.uuid4())
    t = DashboardTemplate(
        id=tid,
        title=title,
        description="desc",
        tiles=[Tile(id="t0", type="kpi", title="KPI")],
        theme=DashboardTheme(),
    )
    save_template(t, templates_dir / f"{tid}.yaml")
    return tid


def test_register_template(tmp_path):
    cat = tmp_path / "cat.jsonl"
    entry = register_template("id1", "Title", "Desc", tags=["sales"], catalogue_path=cat)
    assert entry.template_id == "id1"
    assert entry.title == "Title"
    assert "sales" in entry.tags


def test_register_idempotent(tmp_path):
    cat = tmp_path / "cat.jsonl"
    e1 = register_template("id1", "Title", "Desc", catalogue_path=cat)
    e2 = register_template("id1", "Other Title", "Other", catalogue_path=cat)
    assert e1.template_id == e2.template_id
    assert e2.title == "Title"  # first registration wins


def test_rate_template_updates_average(tmp_path):
    cat = tmp_path / "cat.jsonl"
    register_template("id1", "T", "D", catalogue_path=cat)
    rate_template("id1", 4.0, catalogue_path=cat)
    rate_template("id1", 2.0, catalogue_path=cat)
    entry = get_entry("id1", catalogue_path=cat)
    assert entry.rating_count == 2
    assert abs(entry.rating - 3.0) < 0.01


def test_rate_rejects_out_of_range(tmp_path):
    cat = tmp_path / "cat.jsonl"
    register_template("id1", "T", "D", catalogue_path=cat)
    with pytest.raises(ValueError):
        rate_template("id1", 6.0, catalogue_path=cat)
    with pytest.raises(ValueError):
        rate_template("id1", -1.0, catalogue_path=cat)


def test_rate_unknown_template_raises(tmp_path):
    cat = tmp_path / "cat.jsonl"
    with pytest.raises(ValueError):
        rate_template("nonexistent", 3.0, catalogue_path=cat)


def test_search_by_query(tmp_path):
    cat = tmp_path / "cat.jsonl"
    register_template("id1", "Ventes Québec", "rapport ventes", catalogue_path=cat)
    register_template("id2", "Finance Canada", "rapport finance", catalogue_path=cat)
    results = search_templates(query="ventes", catalogue_path=cat)
    assert len(results) == 1
    assert results[0].template_id == "id1"


def test_search_by_tags(tmp_path):
    cat = tmp_path / "cat.jsonl"
    register_template("id1", "A", "D", tags=["sales", "quebec"], catalogue_path=cat)
    register_template("id2", "B", "D", tags=["finance"], catalogue_path=cat)
    results = search_templates(tags=["sales"], catalogue_path=cat)
    assert len(results) == 1 and results[0].template_id == "id1"


def test_search_sorted_by_use_count(tmp_path):
    cat = tmp_path / "cat.jsonl"
    register_template("id1", "A", "D", catalogue_path=cat)
    register_template("id2", "B", "D", catalogue_path=cat)
    tdir = tmp_path / "templates"
    # Clone id1 twice to increase use_count
    _make_template(tdir, "A")  # dummy for clone source
    import uuid
    tid = str(uuid.uuid4())
    from app.dashboards.models import Tile, DashboardTheme, DashboardTemplate, save_template as st
    t = DashboardTemplate(id="id1", title="A", description="D", tiles=[], theme=DashboardTheme())
    st(t, tdir / "id1.yaml")
    clone_template("id1", "A2", catalogue_path=cat, templates_dir=tdir)
    results = search_templates(catalogue_path=cat)
    assert results[0].template_id == "id1"


def test_clone_increments_use_count(tmp_path):
    cat = tmp_path / "cat.jsonl"
    tdir = tmp_path / "templates"
    register_template("id1", "T", "D", catalogue_path=cat)
    from app.dashboards.models import Tile, DashboardTheme, DashboardTemplate, save_template as st
    t = DashboardTemplate(id="id1", title="T", description="D", tiles=[], theme=DashboardTheme())
    st(t, tdir / "id1.yaml")
    clone_template("id1", "T copy", catalogue_path=cat, templates_dir=tdir)
    entry = get_entry("id1", catalogue_path=cat)
    assert entry.use_count == 1


def test_list_tags(tmp_path):
    cat = tmp_path / "cat.jsonl"
    register_template("id1", "A", "D", tags=["sales", "quebec"], catalogue_path=cat)
    register_template("id2", "B", "D", tags=["finance", "sales"], catalogue_path=cat)
    tags = list_tags(catalogue_path=cat)
    assert "sales" in tags
    assert "finance" in tags
    assert "quebec" in tags
    assert tags == sorted(tags)


def test_list_entries(tmp_path):
    cat = tmp_path / "cat.jsonl"
    register_template("id1", "A", "D", catalogue_path=cat)
    register_template("id2", "B", "D", catalogue_path=cat)
    entries = list_entries(catalogue_path=cat)
    assert len(entries) == 2

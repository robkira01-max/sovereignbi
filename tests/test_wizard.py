"""Tests du wizard de création guidée de templates."""
import pytest
from pathlib import Path
from app.templates.wizard import (
    new_session,
    get_session,
    list_available_metrics,
    list_available_dimensions,
    step_select_metrics,
    step_select_dimensions,
    step_generate_preview,
    step_confirm,
)


MODEL_PATH = "semantic/model.yaml"


def test_new_session_has_step_metrics(tmp_path):
    session = new_session(sessions_path=tmp_path / "s.jsonl")
    assert session.step == "metrics"
    assert session.session_id


def test_new_session_is_persisted(tmp_path):
    p = tmp_path / "s.jsonl"
    session = new_session(sessions_path=p)
    loaded = get_session(session.session_id, sessions_path=p)
    assert loaded is not None
    assert loaded.session_id == session.session_id


def test_session_not_found_returns_none(tmp_path):
    result = get_session("nonexistent-id", sessions_path=tmp_path / "s.jsonl")
    assert result is None


def test_list_available_metrics_from_yaml():
    metrics = list_available_metrics(MODEL_PATH)
    assert isinstance(metrics, list)
    assert len(metrics) >= 1
    assert all("name" in m and "description" in m for m in metrics)


def test_list_available_dimensions_from_yaml():
    dims = list_available_dimensions(MODEL_PATH)
    assert isinstance(dims, list)
    assert len(dims) >= 1
    assert all("table" in d and "column" in d and "key" in d for d in dims)


def test_step_metrics_advances_to_dimensions(tmp_path):
    p = tmp_path / "s.jsonl"
    session = new_session(sessions_path=p)
    metrics = list_available_metrics(MODEL_PATH)
    first_metric = metrics[0]["name"]
    updated = step_select_metrics(session.session_id, [first_metric], sessions_path=p, model_path=MODEL_PATH)
    assert updated.step == "dimensions"
    assert first_metric in updated.selected_metrics


def test_step_metrics_rejects_unknown_metric(tmp_path):
    p = tmp_path / "s.jsonl"
    session = new_session(sessions_path=p)
    with pytest.raises(ValueError, match="inconnues"):
        step_select_metrics(session.session_id, ["metric_inexistante_xyz"], sessions_path=p, model_path=MODEL_PATH)


def test_step_metrics_rejects_empty_list(tmp_path):
    p = tmp_path / "s.jsonl"
    session = new_session(sessions_path=p)
    with pytest.raises(ValueError):
        step_select_metrics(session.session_id, [], sessions_path=p, model_path=MODEL_PATH)


def test_step_dimensions_advances_to_preview(tmp_path):
    p = tmp_path / "s.jsonl"
    session = new_session(sessions_path=p)
    metrics = list_available_metrics(MODEL_PATH)
    dims = list_available_dimensions(MODEL_PATH)
    step_select_metrics(session.session_id, [metrics[0]["name"]], sessions_path=p, model_path=MODEL_PATH)
    updated = step_select_dimensions(session.session_id, [dims[0]["key"]], sessions_path=p, model_path=MODEL_PATH)
    assert updated.step == "preview"
    assert dims[0]["key"] in updated.selected_dimensions


def test_step_generate_preview_requires_preview_step(tmp_path):
    p = tmp_path / "s.jsonl"
    session = new_session(sessions_path=p)
    with pytest.raises(ValueError):
        step_generate_preview(session.session_id, "Test", sessions_path=p, model_path=MODEL_PATH)


def _make_preview_session(tmp_path):
    p = tmp_path / "s.jsonl"
    session = new_session(sessions_path=p)
    metrics = list_available_metrics(MODEL_PATH)
    dims = list_available_dimensions(MODEL_PATH)
    step_select_metrics(session.session_id, [metrics[0]["name"]], sessions_path=p, model_path=MODEL_PATH)
    step_select_dimensions(session.session_id, [dims[0]["key"]], sessions_path=p, model_path=MODEL_PATH)
    return session.session_id, p, metrics[0]["name"], dims[0]["key"]


def test_step_generate_preview_creates_tiles(tmp_path):
    sid, p, _, _ = _make_preview_session(tmp_path)
    session = step_generate_preview(sid, "Mon Template", sessions_path=p, model_path=MODEL_PATH)
    assert len(session.generated_tiles) >= 1
    assert session.template_name == "Mon Template"


def test_step_generate_preview_creates_kpi_tile(tmp_path):
    sid, p, _, _ = _make_preview_session(tmp_path)
    session = step_generate_preview(sid, "T", sessions_path=p, model_path=MODEL_PATH)
    kpi_tiles = [t for t in session.generated_tiles if t["type"] == "kpi"]
    assert len(kpi_tiles) >= 1


def test_step_generate_preview_creates_bar_tile_per_metric_x_dimension(tmp_path):
    sid, p, _, _ = _make_preview_session(tmp_path)
    session = step_generate_preview(sid, "T", sessions_path=p, model_path=MODEL_PATH)
    bar_tiles = [t for t in session.generated_tiles if t["type"] == "bar"]
    assert len(bar_tiles) >= 1


def test_step_confirm_creates_template(tmp_path):
    sid, p, _, _ = _make_preview_session(tmp_path)
    step_generate_preview(sid, "Mon Template", sessions_path=p, model_path=MODEL_PATH)
    result = step_confirm(sid, sessions_path=p, templates_dir=tmp_path / "templates")
    assert "template_id" in result
    assert result["tile_count"] >= 1
    # Template file created
    assert (tmp_path / "templates" / f"{result['template_id']}.yaml").exists()


def test_step_confirm_requires_preview_step(tmp_path):
    p = tmp_path / "s.jsonl"
    session = new_session(sessions_path=p)
    with pytest.raises(ValueError):
        step_confirm(session.session_id, sessions_path=p, templates_dir=tmp_path / "templates")


def test_step_confirm_sets_done_step(tmp_path):
    sid, p, _, _ = _make_preview_session(tmp_path)
    step_generate_preview(sid, "T", sessions_path=p, model_path=MODEL_PATH)
    step_confirm(sid, sessions_path=p, templates_dir=tmp_path / "templates")
    session = get_session(sid, sessions_path=p)
    assert session.step == "done"

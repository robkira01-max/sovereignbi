"""Tests pour app/alerts/models.py."""
import pytest
from app.alerts.models import (
    create_rule, get_rule, list_rules, update_rule, delete_rule,
    save_event, list_events, AlertEvent
)
import uuid


def _rule_kwargs(tmp_path):
    return dict(
        name="Test rule",
        question="SELECT COUNT(*) AS cnt FROM sales",
        condition="gt",
        threshold=100.0,
        column="cnt",
        schedule_minutes=10,
        alerts_path=tmp_path / "alerts.jsonl",
    )


def test_create_rule(tmp_path):
    rule = create_rule(**_rule_kwargs(tmp_path))
    assert rule.rule_id
    assert rule.name == "Test rule"
    assert rule.condition == "gt"
    assert rule.enabled is True


def test_create_rule_validates_schedule_min_5(tmp_path):
    kwargs = _rule_kwargs(tmp_path)
    kwargs["schedule_minutes"] = 4
    with pytest.raises(ValueError, match="5"):
        create_rule(**kwargs)


def test_create_rule_validates_condition(tmp_path):
    kwargs = _rule_kwargs(tmp_path)
    kwargs["condition"] = "invalid"
    with pytest.raises(ValueError):
        create_rule(**kwargs)


def test_get_rule(tmp_path):
    rule = create_rule(**_rule_kwargs(tmp_path))
    path = tmp_path / "alerts.jsonl"
    found = get_rule(rule.rule_id, alerts_path=path)
    assert found is not None
    assert found.rule_id == rule.rule_id


def test_get_rule_not_found(tmp_path):
    path = tmp_path / "alerts.jsonl"
    assert get_rule("nonexistent", alerts_path=path) is None


def test_list_rules(tmp_path):
    path = tmp_path / "alerts.jsonl"
    kwargs = _rule_kwargs(tmp_path)
    kwargs["alerts_path"] = path
    create_rule(**kwargs)
    kwargs2 = kwargs.copy()
    kwargs2["name"] = "Rule 2"
    create_rule(**kwargs2)
    rules = list_rules(alerts_path=path)
    assert len(rules) == 2


def test_update_rule(tmp_path):
    path = tmp_path / "alerts.jsonl"
    kwargs = _rule_kwargs(tmp_path)
    kwargs["alerts_path"] = path
    rule = create_rule(**kwargs)
    updated = update_rule(rule.rule_id, alerts_path=path, name="Updated", threshold=200.0)
    assert updated.name == "Updated"
    assert updated.threshold == 200.0


def test_update_rule_not_found(tmp_path):
    path = tmp_path / "alerts.jsonl"
    with pytest.raises(KeyError):
        update_rule("nonexistent", alerts_path=path, name="x")


def test_delete_rule(tmp_path):
    path = tmp_path / "alerts.jsonl"
    kwargs = _rule_kwargs(tmp_path)
    kwargs["alerts_path"] = path
    rule = create_rule(**kwargs)
    assert delete_rule(rule.rule_id, alerts_path=path) is True
    assert get_rule(rule.rule_id, alerts_path=path) is None


def test_delete_rule_not_found(tmp_path):
    path = tmp_path / "alerts.jsonl"
    assert delete_rule("nonexistent", alerts_path=path) is False


def _make_event(rule_id="r1"):
    return AlertEvent(
        event_id=str(uuid.uuid4()),
        rule_id=rule_id,
        rule_name="Test",
        triggered_at="2026-01-01T00:00:00+00:00",
        value=150.0,
        threshold=100.0,
        condition="gt",
        status="triggered",
        message="150.0 gt 100.0 → ALERTE",
    )


def test_save_and_list_events(tmp_path):
    path = tmp_path / "history.jsonl"
    e = _make_event()
    save_event(e, history_path=path)
    events = list_events(history_path=path)
    assert len(events) == 1
    assert events[0].event_id == e.event_id


def test_list_events_filter_by_rule(tmp_path):
    path = tmp_path / "history.jsonl"
    save_event(_make_event("rule-a"), history_path=path)
    save_event(_make_event("rule-b"), history_path=path)
    events = list_events(rule_id="rule-a", history_path=path)
    assert len(events) == 1
    assert events[0].rule_id == "rule-a"

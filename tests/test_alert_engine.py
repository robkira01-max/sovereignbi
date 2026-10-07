"""Tests pour app/alerts/engine.py."""
import pandas as pd
import pytest
from app.alerts.engine import CONDITION_FNS, evaluate_rule, run_due_rules
from app.alerts.models import create_rule, AlertRule
from app.data.duckdb_store import DataStore
from datetime import datetime, timezone, timedelta


def _store_with_data():
    store = DataStore()
    store.load_dataframe("sales", pd.DataFrame({"cnt": [150], "revenue": [5000.0]}))
    return store


def _make_rule(**kwargs):
    defaults = dict(
        rule_id="r1",
        name="Test",
        question="SELECT cnt FROM sales",
        condition="gt",
        threshold=100.0,
        column="cnt",
        schedule_minutes=10,
    )
    defaults.update(kwargs)
    return AlertRule(**defaults)


def test_evaluate_rule_triggered():
    store = _store_with_data()
    rule = _make_rule(condition="gt", threshold=100.0)
    event = evaluate_rule(rule, store)
    assert event.status == "triggered"
    assert event.value == 150.0


def test_evaluate_rule_resolved():
    store = _store_with_data()
    rule = _make_rule(condition="gt", threshold=200.0)
    event = evaluate_rule(rule, store)
    assert event.status == "resolved"


def test_evaluate_rule_error_on_bad_sql():
    store = _store_with_data()
    rule = _make_rule(question="SELECT nonexistent FROM sales")
    event = evaluate_rule(rule, store)
    assert event.status == "error"


def test_evaluate_rule_error_missing_column():
    store = _store_with_data()
    rule = _make_rule(column="missing_col")
    event = evaluate_rule(rule, store)
    assert event.status == "error"


def test_condition_gt():
    assert CONDITION_FNS["gt"](5, 3) is True
    assert CONDITION_FNS["gt"](3, 5) is False


def test_condition_lt():
    assert CONDITION_FNS["lt"](3, 5) is True
    assert CONDITION_FNS["lt"](5, 3) is False


def test_condition_eq():
    assert CONDITION_FNS["eq"](5.0, 5.0) is True
    assert CONDITION_FNS["eq"](5.0, 5.1) is False


def test_condition_gte():
    assert CONDITION_FNS["gte"](5, 5) is True
    assert CONDITION_FNS["gte"](4, 5) is False


def test_condition_lte():
    assert CONDITION_FNS["lte"](5, 5) is True
    assert CONDITION_FNS["lte"](6, 5) is False


def test_run_due_rules_skips_disabled(tmp_path):
    store = _store_with_data()
    apath = tmp_path / "alerts.jsonl"
    hpath = tmp_path / "history.jsonl"
    create_rule(
        name="disabled", question="SELECT cnt FROM sales",
        condition="gt", threshold=100.0, column="cnt",
        schedule_minutes=5, alerts_path=apath,
    )
    from app.alerts.models import update_rule, list_rules
    rules = list_rules(alerts_path=apath)
    update_rule(rules[0].rule_id, alerts_path=apath, enabled=False)
    events = run_due_rules(store, alerts_path=apath, history_path=hpath)
    assert events == []


def test_run_due_rules_skips_not_due(tmp_path):
    store = _store_with_data()
    apath = tmp_path / "alerts.jsonl"
    hpath = tmp_path / "history.jsonl"
    create_rule(
        name="recent", question="SELECT cnt FROM sales",
        condition="gt", threshold=100.0, column="cnt",
        schedule_minutes=60, alerts_path=apath,
    )
    from app.alerts.models import update_rule, list_rules
    rules = list_rules(alerts_path=apath)
    recent = datetime.now(tz=timezone.utc).isoformat()
    update_rule(rules[0].rule_id, alerts_path=apath, last_run=recent)
    events = run_due_rules(store, alerts_path=apath, history_path=hpath)
    assert events == []


def test_run_due_rules_evaluates_due(tmp_path):
    store = _store_with_data()
    apath = tmp_path / "alerts.jsonl"
    hpath = tmp_path / "history.jsonl"
    create_rule(
        name="due", question="SELECT cnt FROM sales",
        condition="gt", threshold=100.0, column="cnt",
        schedule_minutes=5, alerts_path=apath,
    )
    events = run_due_rules(store, alerts_path=apath, history_path=hpath)
    assert len(events) == 1
    assert events[0].status == "triggered"


def test_run_due_rules_updates_last_run(tmp_path):
    store = _store_with_data()
    apath = tmp_path / "alerts.jsonl"
    hpath = tmp_path / "history.jsonl"
    create_rule(
        name="track", question="SELECT cnt FROM sales",
        condition="gt", threshold=100.0, column="cnt",
        schedule_minutes=5, alerts_path=apath,
    )
    run_due_rules(store, alerts_path=apath, history_path=hpath)
    from app.alerts.models import list_rules
    rules = list_rules(alerts_path=apath)
    assert rules[0].last_run is not None
    assert rules[0].last_value == 150.0

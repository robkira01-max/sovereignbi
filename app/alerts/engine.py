"""Évaluation des règles d'alerte contre le DataStore."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.alerts.models import (
    ALERT_HISTORY_PATH,
    ALERTS_PATH,
    AlertEvent,
    AlertRule,
    list_rules,
    save_event,
    update_rule,
)

CONDITION_FNS = {
    "gt": lambda v, t: v > t,
    "lt": lambda v, t: v < t,
    "eq": lambda v, t: abs(v - t) < 1e-9,
    "gte": lambda v, t: v >= t,
    "lte": lambda v, t: v <= t,
}


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def evaluate_rule(rule: AlertRule, store) -> AlertEvent:
    """Execute rule.question SQL, read rule.column from first row, compare to threshold."""
    triggered_at = _now().isoformat()
    try:
        from app.security.sql_guard import validate_sql
        safe = validate_sql(rule.question, store.tables)
        cols, rows = store.execute(safe)
        if not rows:
            return AlertEvent(
                event_id=str(uuid.uuid4()),
                rule_id=rule.rule_id,
                rule_name=rule.name,
                triggered_at=triggered_at,
                value=0.0,
                threshold=rule.threshold,
                condition=rule.condition,
                status="error",
                message="Query returned no rows",
            )
        col_names = [c.lower() for c in cols]
        col_key = rule.column.lower()
        if col_key not in col_names:
            return AlertEvent(
                event_id=str(uuid.uuid4()),
                rule_id=rule.rule_id,
                rule_name=rule.name,
                triggered_at=triggered_at,
                value=0.0,
                threshold=rule.threshold,
                condition=rule.condition,
                status="error",
                message=f"Column {rule.column!r} not found in results",
            )
        idx = col_names.index(col_key)
        value = float(rows[0][idx])
        fn = CONDITION_FNS[rule.condition]
        triggered = fn(value, rule.threshold)
        return AlertEvent(
            event_id=str(uuid.uuid4()),
            rule_id=rule.rule_id,
            rule_name=rule.name,
            triggered_at=triggered_at,
            value=value,
            threshold=rule.threshold,
            condition=rule.condition,
            status="triggered" if triggered else "resolved",
            message=f"{value} {rule.condition} {rule.threshold} → {'ALERTE' if triggered else 'OK'}",
        )
    except Exception as e:
        return AlertEvent(
            event_id=str(uuid.uuid4()),
            rule_id=rule.rule_id,
            rule_name=rule.name,
            triggered_at=triggered_at,
            value=0.0,
            threshold=rule.threshold,
            condition=rule.condition,
            status="error",
            message=str(e),
        )


def run_due_rules(
    store,
    alerts_path: Path = ALERTS_PATH,
    history_path: Path = ALERT_HISTORY_PATH,
) -> list[AlertEvent]:
    """Evaluate all enabled rules that are due."""
    now = _now()
    rules = list_rules(alerts_path)
    events = []
    for rule in rules:
        if not rule.enabled:
            continue
        if rule.last_run is not None:
            last = datetime.fromisoformat(rule.last_run)
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            due_at = last + timedelta(minutes=rule.schedule_minutes)
            if now < due_at:
                continue
        event = evaluate_rule(rule, store)
        update_rule(
            rule.rule_id,
            alerts_path=alerts_path,
            last_run=now.isoformat(),
            last_value=event.value,
        )
        save_event(event, history_path)
        events.append(event)
    return events

"""Modèle de données pour les alertes et règles de surveillance."""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

ALERTS_PATH = Path("data/alerts.jsonl")
ALERT_HISTORY_PATH = Path("data/alert_history.jsonl")

VALID_CONDITIONS = {"gt", "lt", "eq", "gte", "lte"}


@dataclass
class AlertRule:
    rule_id: str
    name: str
    question: str
    condition: str
    threshold: float
    column: str
    schedule_minutes: int
    enabled: bool = True
    created_at: str = ""
    last_run: str | None = None
    last_value: float | None = None


@dataclass
class AlertEvent:
    event_id: str
    rule_id: str
    rule_name: str
    triggered_at: str
    value: float
    threshold: float
    condition: str
    status: Literal["triggered", "resolved", "error"]
    message: str


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _load_rules(alerts_path: Path) -> list[AlertRule]:
    if not alerts_path.exists():
        return []
    rules = []
    for line in alerts_path.read_text().splitlines():
        line = line.strip()
        if line:
            d = json.loads(line)
            rules.append(AlertRule(**d))
    return rules


def _save_rules(rules: list[AlertRule], alerts_path: Path) -> None:
    alerts_path.parent.mkdir(parents=True, exist_ok=True)
    alerts_path.write_text("\n".join(json.dumps(asdict(r)) for r in rules) + ("\n" if rules else ""))


def create_rule(
    name: str,
    question: str,
    condition: str,
    threshold: float,
    column: str,
    schedule_minutes: int,
    alerts_path: Path = ALERTS_PATH,
) -> AlertRule:
    if schedule_minutes < 5:
        raise ValueError("schedule_minutes must be >= 5")
    if condition not in VALID_CONDITIONS:
        raise ValueError(f"condition must be one of {VALID_CONDITIONS}")
    rule = AlertRule(
        rule_id=str(uuid.uuid4()),
        name=name,
        question=question,
        condition=condition,
        threshold=threshold,
        column=column,
        schedule_minutes=schedule_minutes,
        created_at=_now(),
    )
    rules = _load_rules(alerts_path)
    rules.append(rule)
    _save_rules(rules, alerts_path)
    return rule


def get_rule(rule_id: str, alerts_path: Path = ALERTS_PATH) -> AlertRule | None:
    for r in _load_rules(alerts_path):
        if r.rule_id == rule_id:
            return r
    return None


def list_rules(alerts_path: Path = ALERTS_PATH) -> list[AlertRule]:
    return _load_rules(alerts_path)


def update_rule(rule_id: str, alerts_path: Path = ALERTS_PATH, **kwargs) -> AlertRule:
    rules = _load_rules(alerts_path)
    for i, r in enumerate(rules):
        if r.rule_id == rule_id:
            for k, v in kwargs.items():
                if hasattr(r, k):
                    setattr(r, k, v)
            _save_rules(rules, alerts_path)
            return r
    raise KeyError(f"Rule {rule_id!r} not found")


def delete_rule(rule_id: str, alerts_path: Path = ALERTS_PATH) -> bool:
    rules = _load_rules(alerts_path)
    new_rules = [r for r in rules if r.rule_id != rule_id]
    if len(new_rules) == len(rules):
        return False
    _save_rules(new_rules, alerts_path)
    return True


def save_event(event: AlertEvent, history_path: Path = ALERT_HISTORY_PATH) -> None:
    history_path.parent.mkdir(parents=True, exist_ok=True)
    with history_path.open("a") as f:
        f.write(json.dumps(asdict(event)) + "\n")


def list_events(
    rule_id: str | None = None,
    limit: int = 50,
    history_path: Path = ALERT_HISTORY_PATH,
) -> list[AlertEvent]:
    if not history_path.exists():
        return []
    events = []
    for line in history_path.read_text().splitlines():
        line = line.strip()
        if line:
            d = json.loads(line)
            e = AlertEvent(**d)
            if rule_id is None or e.rule_id == rule_id:
                events.append(e)
    return events[-limit:]

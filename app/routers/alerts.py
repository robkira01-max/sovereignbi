"""Routes API pour les alertes et règles de surveillance."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.alerts.engine import evaluate_rule, run_due_rules
from app.alerts.models import (
    ALERT_HISTORY_PATH,
    ALERTS_PATH,
    AlertRule,
    create_rule,
    delete_rule,
    get_rule,
    list_events,
    list_rules,
    update_rule,
)
from app.alerts.notifier import load_webhook_url, save_webhook_url
from app.security.rbac import RequireRole

router = APIRouter(prefix="/alerts", tags=["alerts"])

_VIEWER = RequireRole("viewer")
_EDITOR = RequireRole("editor")
_ADMIN = RequireRole("admin")


class RuleCreate(BaseModel):
    name: str
    question: str
    condition: str
    threshold: float
    column: str
    schedule_minutes: int = Field(ge=5)


class RuleUpdate(BaseModel):
    name: str | None = None
    question: str | None = None
    condition: str | None = None
    threshold: float | None = None
    column: str | None = None
    schedule_minutes: int | None = Field(default=None, ge=5)
    enabled: bool | None = None


class WebhookConfig(BaseModel):
    url: str | None = None


def _rule_to_dict(r: AlertRule) -> dict:
    from dataclasses import asdict
    return asdict(r)


@router.post("/rules")
def create_alert_rule(body: RuleCreate, _: str = Depends(_EDITOR)):
    try:
        rule = create_rule(
            name=body.name,
            question=body.question,
            condition=body.condition,
            threshold=body.threshold,
            column=body.column,
            schedule_minutes=body.schedule_minutes,
        )
        return _rule_to_dict(rule)
    except ValueError as e:
        raise HTTPException(422, str(e))


@router.get("/rules")
def list_alert_rules(_: str = Depends(_VIEWER)):
    return [_rule_to_dict(r) for r in list_rules()]


@router.get("/rules/{rule_id}")
def get_alert_rule(rule_id: str, _: str = Depends(_VIEWER)):
    rule = get_rule(rule_id)
    if rule is None:
        raise HTTPException(404, "Rule not found")
    return _rule_to_dict(rule)


@router.put("/rules/{rule_id}")
def update_alert_rule(rule_id: str, body: RuleUpdate, _: str = Depends(_EDITOR)):
    kwargs = {k: v for k, v in body.model_dump().items() if v is not None}
    try:
        rule = update_rule(rule_id, **kwargs)
        return _rule_to_dict(rule)
    except KeyError as e:
        raise HTTPException(404, str(e))


@router.delete("/rules/{rule_id}")
def delete_alert_rule(rule_id: str, _: str = Depends(_EDITOR)):
    if not delete_rule(rule_id):
        raise HTTPException(404, "Rule not found")
    return {"deleted": rule_id}


@router.post("/rules/{rule_id}/run")
def run_rule_now(rule_id: str, request: Request, _: str = Depends(_EDITOR)):
    rule = get_rule(rule_id)
    if rule is None:
        raise HTTPException(404, "Rule not found")
    store = request.app.state.store
    from dataclasses import asdict
    event = evaluate_rule(rule, store)
    return asdict(event)


@router.get("/history")
def get_history(
    rule_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    _: str = Depends(_VIEWER),
):
    from dataclasses import asdict
    return [asdict(e) for e in list_events(rule_id=rule_id, limit=limit)]


@router.get("/history/{rule_id}")
def get_rule_history(rule_id: str, _: str = Depends(_VIEWER)):
    from dataclasses import asdict
    return [asdict(e) for e in list_events(rule_id=rule_id)]


@router.post("/webhook")
def configure_webhook(body: WebhookConfig, _: str = Depends(_ADMIN)):
    save_webhook_url(body.url)
    return {"configured": body.url is not None}


@router.get("/webhook")
def get_webhook_status(_: str = Depends(_ADMIN)):
    url = load_webhook_url()
    return {"configured": url is not None}

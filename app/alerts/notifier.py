"""Dispatching des notifications d'alerte."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from app.alerts.models import AlertEvent

WEBHOOK_CONFIG_PATH = Path("data/alert_webhook.json")


class Notifier(Protocol):
    def send(self, event: AlertEvent) -> bool: ...


@dataclass
class LogNotifier:
    """Write alert events to a local JSONL file — always available fallback."""
    path: str = "data/alert_notifications.jsonl"

    def send(self, event: AlertEvent) -> bool:
        try:
            p = Path(self.path)
            p.parent.mkdir(parents=True, exist_ok=True)
            with p.open("a") as f:
                f.write(json.dumps(asdict(event)) + "\n")
            return True
        except Exception:
            return False


@dataclass
class WebhookNotifier:
    """POST JSON to a webhook URL; circuit breaker after 3 consecutive failures."""
    url: str
    _failures: int = field(default=0, repr=False)
    MAX_FAILURES: int = field(default=3, repr=False)

    def send(self, event: AlertEvent) -> bool:
        if self._failures >= self.MAX_FAILURES:
            return False
        try:
            import httpx
            payload = {**asdict(event), "sent_at": datetime.now(tz=timezone.utc).isoformat()}
            r = httpx.post(self.url, json=payload, timeout=5.0)
            r.raise_for_status()
            self._failures = 0
            return True
        except Exception:
            self._failures += 1
            return False


def get_notifiers(webhook_url: str | None = None) -> list:
    notifiers: list = [LogNotifier()]
    if webhook_url:
        notifiers.insert(0, WebhookNotifier(url=webhook_url))
    return notifiers


def save_webhook_url(url: str | None, config_path: Path = WEBHOOK_CONFIG_PATH) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps({"url": url}))


def load_webhook_url(config_path: Path = WEBHOOK_CONFIG_PATH) -> str | None:
    if not config_path.exists():
        return None
    data = json.loads(config_path.read_text())
    return data.get("url")

"""Tests pour app/alerts/notifier.py."""
import json
import uuid
from unittest.mock import MagicMock, patch
from app.alerts.models import AlertEvent
from app.alerts.notifier import LogNotifier, WebhookNotifier, get_notifiers


def _event():
    return AlertEvent(
        event_id=str(uuid.uuid4()),
        rule_id="r1",
        rule_name="Test",
        triggered_at="2026-01-01T00:00:00+00:00",
        value=150.0,
        threshold=100.0,
        condition="gt",
        status="triggered",
        message="test",
    )


def test_log_notifier_writes_to_file(tmp_path):
    path = str(tmp_path / "notif.jsonl")
    n = LogNotifier(path=path)
    result = n.send(_event())
    assert result is True
    lines = (tmp_path / "notif.jsonl").read_text().strip().splitlines()
    assert len(lines) == 1
    data = json.loads(lines[0])
    assert data["status"] == "triggered"


def test_log_notifier_multiple_events(tmp_path):
    path = str(tmp_path / "notif.jsonl")
    n = LogNotifier(path=path)
    n.send(_event())
    n.send(_event())
    lines = (tmp_path / "notif.jsonl").read_text().strip().splitlines()
    assert len(lines) == 2


def test_webhook_notifier_sends_post():
    with patch("httpx.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp
        n = WebhookNotifier(url="http://example.com/hook")
        result = n.send(_event())
        assert result is True
        assert mock_post.called
        call_kwargs = mock_post.call_args
        assert call_kwargs[0][0] == "http://example.com/hook"


def test_webhook_notifier_circuit_breaker():
    with patch("httpx.post", side_effect=Exception("connection failed")):
        n = WebhookNotifier(url="http://example.com/hook", MAX_FAILURES=3)
        n.send(_event())
        n.send(_event())
        n.send(_event())
        # Now at MAX_FAILURES, next call should return False without calling httpx
        with patch("httpx.post") as mock_post:
            result = n.send(_event())
            assert result is False
            assert not mock_post.called


def test_get_notifiers_without_webhook():
    notifiers = get_notifiers(webhook_url=None)
    assert len(notifiers) == 1
    assert isinstance(notifiers[0], LogNotifier)


def test_get_notifiers_with_webhook():
    notifiers = get_notifiers(webhook_url="http://example.com/hook")
    assert len(notifiers) == 2
    assert isinstance(notifiers[0], WebhookNotifier)
    assert isinstance(notifiers[1], LogNotifier)

"""Envoi de courriels. SMTP si configuré, sinon boîte d'envoi locale (aucun envoi réel)."""
from __future__ import annotations

import os
import smtplib
import ssl
import uuid
from email.message import EmailMessage
from pathlib import Path

OUTBOX = Path(os.environ.get("SOVEREIGN_OUTBOX_DIR", "data/outbox"))


class MailError(RuntimeError):
    pass


def smtp_configured() -> bool:
    return bool(os.environ.get("SMTP_HOST"))


def build(to: str, subject: str, html: str, text: str, unsubscribe_url: str | None = None) -> EmailMessage:
    if any(c in (to + subject) for c in "\r\n"):
        raise MailError("Caractère de fin de ligne interdit dans l'adresse ou le sujet.")
    m = EmailMessage()
    m["From"] = os.environ.get("SMTP_FROM", "mizanbi@localhost")
    m["To"] = to
    m["Subject"] = subject
    if unsubscribe_url:
        m["List-Unsubscribe"] = f"<{unsubscribe_url}>"
    m.set_content(text)
    m.add_alternative(html, subtype="html")
    return m


def send(msg: EmailMessage) -> str:
    """Retourne « smtp » ou « outbox ». Lève MailError en cas d'échec (sans exposer d'identifiants)."""
    if not smtp_configured():
        OUTBOX.mkdir(parents=True, exist_ok=True)
        (OUTBOX / f"{uuid.uuid4().hex}.eml").write_bytes(bytes(msg))
        return "outbox"
    host, port = os.environ["SMTP_HOST"], int(os.environ.get("SMTP_PORT", "587"))
    try:
        ctx = ssl.create_default_context()
        if port == 465:
            with smtplib.SMTP_SSL(host, port, context=ctx, timeout=15) as s:
                _login_send(s, msg)
        else:
            with smtplib.SMTP(host, port, timeout=15) as s:
                s.starttls(context=ctx)          # STARTTLS obligatoire : pas de repli en clair
                _login_send(s, msg)
    except (OSError, smtplib.SMTPException) as e:
        raise MailError(f"Échec SMTP ({type(e).__name__})") from None
    return "smtp"


def _login_send(s: smtplib.SMTP, msg: EmailMessage) -> None:
    user = os.environ.get("SMTP_USER")
    if user:
        s.login(user, os.environ.get("SMTP_PASSWORD", ""))
    s.send_message(msg)

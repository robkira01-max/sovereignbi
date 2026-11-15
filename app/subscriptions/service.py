"""Génération et envoi d'un bulletin d'abonnement, et tâche périodique."""
from __future__ import annotations

import html as _html
import os
import re
from datetime import datetime
from pathlib import Path

import structlog

from app.security import row_policy
from app.subscriptions import mailer, store

log = structlog.get_logger()
_ID_RE = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")


def unsubscribe_url(sub: store.Subscription) -> str | None:
    base = os.environ.get("SOVEREIGN_PUBLIC_URL", "").rstrip("/")
    if not base.startswith("https://"):
        return None            # sans URL publique HTTPS, pas de lien (le destinataire est prié de répondre)
    return f"{base}/subscriptions/unsubscribe?id={sub.id}&token={store.unsubscribe_token(sub)}"


def send_one(sub: store.Subscription, store_data, dashboards_dir: Path, now: datetime | None = None) -> str:
    """Envoie le bulletin à un abonné ; met à jour last_sent_at / last_error. Retourne « smtp » ou « outbox »."""
    from app.dashboards.bulletin import generate_bulletin_html
    from app.dashboards.models import load_dashboard

    now = now or store.now_utc()
    try:
        if not _ID_RE.match(sub.dashboard_id):
            raise mailer.MailError("Identifiant de tableau de bord invalide.")
        p = dashboards_dir / f"{sub.dashboard_id}.yaml"
        if not p.exists():
            raise mailer.MailError("Tableau de bord introuvable (supprimé ?).")
        d = load_dashboard(p)
        with row_policy.as_principal(None):   # un courriel ne part jamais avec les droits de celui qui déclenche l'envoi (P-068)
            body = generate_bulletin_html(d, store_data)
        url = unsubscribe_url(sub)
        footer_html = (f'<p style="font-size:12px;color:#6b7280">Pour ne plus recevoir ce bulletin : '
                       f'<a href="{_html.escape(url)}">se désabonner</a>.</p>') if url else \
            '<p style="font-size:12px;color:#6b7280">Pour ne plus recevoir ce bulletin, contactez votre administrateur.</p>'
        text = (f"Bulletin « {d.title} » — {now:%d/%m/%Y}.\nOuvrez ce message en HTML pour voir les tableaux."
                + (f"\nSe désabonner : {url}" if url else ""))
        msg = mailer.build(sub.email, f"Bulletin — {d.title}", body.replace("</body>", footer_html + "</body>"), text, url)
        channel = mailer.send(msg)
    except Exception as e:  # noqa: BLE001 - l'échec d'un abonné ne doit pas bloquer les autres
        sub.last_error = str(e)[:200]
        store.update(sub)
        log.warning("subscription_failed", subscription=sub.id, error_type=type(e).__name__)
        raise
    sub.last_sent_at = now.isoformat()
    sub.last_error = None
    store.update(sub)
    log.info("subscription_sent", subscription=sub.id, channel=channel)
    return channel


def run_due(store_data, dashboards_dir: Path, now: datetime | None = None) -> dict:
    """Envoie les bulletins échus. Une seule tentative par abonné et par passage (pas de boucle de relance)."""
    now = now or store.now_utc()
    sent = failed = 0
    for sub in store.list_all():
        if not store.is_due(sub, now):
            continue
        try:
            send_one(sub, store_data, dashboards_dir, now)
            sent += 1
        except Exception:  # noqa: BLE001
            failed += 1
            # on marque l'échéance comme tentée pour ne pas réessayer chaque minute ; l'erreur reste visible
            sub.last_sent_at = now.isoformat()
            store.update(sub)
    return {"sent": sent, "failed": failed}

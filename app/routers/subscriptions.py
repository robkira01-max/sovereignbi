"""Abonnements courriel aux bulletins (P-067)."""
from __future__ import annotations

import html

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app.security.rbac import RequireRole
from app.subscriptions import mailer, service, store

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])
_VIEWER, _EDITOR = RequireRole("viewer"), RequireRole("editor")


class SubscriptionCreate(BaseModel):
    dashboard_id: str = Field(max_length=64)
    email: str = Field(max_length=254)
    frequency: str = "weekly"
    hour_utc: int = 7
    weekday: int = 0
    day_of_month: int = 1


def _public(s: store.Subscription) -> dict:
    return {k: v for k, v in s.__dict__.items() if k != "unsub_secret"}


def _dash_dir():
    import app.routers.dashboards as d
    return d._DASHBOARDS_DIR


@router.get("/status")
def status(_: str = Depends(_VIEWER)):
    return {"smtp_configured": mailer.smtp_configured(), "mode": "smtp" if mailer.smtp_configured() else "outbox (aucun envoi réel)"}


@router.get("")
def list_subscriptions(dashboard_id: str | None = Query(None, max_length=64), _: str = Depends(_EDITOR)):
    items = [s for s in store.list_all() if dashboard_id in (None, s.dashboard_id)]
    return {"count": len(items), "subscriptions": [_public(s) for s in items]}


@router.post("", status_code=201)
def create(body: SubscriptionCreate, request: Request, who: str = Depends(_EDITOR)):
    try:
        email = store.validate(body.dashboard_id, body.email, body.frequency, body.hour_utc, body.weekday, body.day_of_month)
        if not (_dash_dir() / f"{body.dashboard_id}.yaml").exists():
            raise store.SubscriptionError("Tableau de bord introuvable.")
        sub = store.add(store.Subscription(
            id=store.new_id(), dashboard_id=body.dashboard_id, email=email, frequency=body.frequency,
            hour_utc=body.hour_utc, weekday=body.weekday, day_of_month=body.day_of_month,
            created_by=str(who)[:64], created_at=store.now_utc().isoformat()))
    except store.SubscriptionError as e:
        raise HTTPException(409 if "déjà" in str(e) else 422, str(e)) from None
    return _public(sub)


@router.delete("/{sub_id}", status_code=204)
def delete(sub_id: str, _: str = Depends(_EDITOR)):
    if not store.remove(sub_id):
        raise HTTPException(404, "Abonnement introuvable.")


@router.post("/{sub_id}/send-now")
def send_now(sub_id: str, request: Request, _: str = Depends(_EDITOR)):
    sub = store.get(sub_id)
    if sub is None:
        raise HTTPException(404, "Abonnement introuvable.")
    try:
        channel = service.send_one(sub, request.app.state.store, _dash_dir())
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"Envoi impossible : {str(e)[:200]}") from None
    return {"sent": True, "channel": channel}


# Désabonnement : seule route sans RequireRole — protégée par un jeton HMAC par abonné.
# GET n'affiche qu'un formulaire (les antivirus de messagerie préchargent les liens) ; POST supprime.
@router.get("/unsubscribe", response_class=HTMLResponse)
def unsubscribe_form(id: str = Query(max_length=32), token: str = Query(max_length=128)):
    sub = store.get(id)
    if sub is None or not store.check_unsubscribe_token(sub, token):
        raise HTTPException(404, "Lien invalide ou déjà utilisé.")
    return HTMLResponse(
        "<!doctype html><meta charset=utf-8><meta name=robots content=noindex><title>Désabonnement</title>"
        "<form method=post style='font-family:sans-serif;max-width:28rem;margin:4rem auto'>"
        f"<p>Ne plus recevoir le bulletin à l'adresse <b>{html.escape(sub.email)}</b> ?</p>"
        f"<input type=hidden name=id value='{html.escape(id)}'><input type=hidden name=token value='{html.escape(token)}'>"
        "<button>Me désabonner</button></form>",
        headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})


@router.post("/unsubscribe", response_class=HTMLResponse)
def unsubscribe(id: str = Form(max_length=32), token: str = Form(max_length=128)):
    sub = store.get(id)
    if sub is None or not store.check_unsubscribe_token(sub, token):
        raise HTTPException(404, "Lien invalide ou déjà utilisé.")
    store.remove(id)
    return HTMLResponse("<!doctype html><meta charset=utf-8><title>Désabonné</title><p style='font-family:sans-serif;margin:4rem auto;max-width:28rem'>Vous êtes désabonné.</p>",
                        headers={"Cache-Control": "no-store"})

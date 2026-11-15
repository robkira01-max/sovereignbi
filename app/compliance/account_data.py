"""Export et suppression des données d'un compte (P-064).

Périmètre : compte (e-mail, rôle), sessions, consentements, demandes d'accès (pseudonymisées),
abonnements courriel. **Conservé volontairement** : le journal d'audit chaîné (il ne contient que
l'identifiant numérique du compte, jamais l'e-mail ; le réécrire casserait la chaîne d'intégrité).
Les données analytiques importées par le client ne sont pas rattachées à un compte : leur
restitution/suppression relève du contrat (DPA), pas de cet outil.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from contextlib import closing
from dataclasses import asdict
from pathlib import Path

from app.auth import security as sec
from app.compliance import models
from app.subscriptions import store as subs


class AccountError(ValueError):
    pass


def _lines(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                raise AccountError(f"{path.name} ligne {n} illisible : corrigez le fichier avant de continuer.") from None
    return out


def _rewrite(path: Path, rows: list[dict]) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def _user(user_id: int) -> dict:
    u = sec.get_user(user_id)
    if u is None:
        raise AccountError("Compte introuvable.")
    return u


def export_account(user_id: int) -> dict:
    u = _user(user_id)
    email = u["email"]
    return {
        "account": u,
        "consents": [r for r in _lines(models.CONSENT_PATH) if r.get("user_id") == email],
        "access_requests": [r for r in _lines(models.REQUESTS_PATH) if r.get("user_id") == email],
        "email_subscriptions": [
            {k: v for k, v in asdict(s).items() if k != "unsub_secret"}
            for s in subs.list_all() if s.email == email.lower()
        ],
        "not_included": [
            "journal d'audit (identifiant numérique du compte seulement, conservé pour l'intégrité)",
            "données analytiques importées par le client (hors compte : voir le DPA)",
            "sauvegardes (purgées selon la rétention)",
        ],
    }


def erase_account(user_id: int, confirm_email: str) -> dict:
    u = _user(user_id)
    email = u["email"]
    if confirm_email.strip().lower() != email.lower():
        raise AccountError("Confirmation incorrecte : indiquez l'adresse exacte du compte.")
    with closing(sec._conn()) as c, c:          # commit à la sortie, annulation si exception
        c.execute("BEGIN IMMEDIATE")
        if u["role"] == "admin" and u["is_active"]:
            others = c.execute("SELECT COUNT(*) FROM users WHERE role='admin' AND is_active=1 AND id!=?", (user_id,)).fetchone()[0]
            if others == 0:
                raise AccountError("Impossible de supprimer le dernier administrateur actif.")
        sessions = c.execute("DELETE FROM sessions WHERE user_id=?", (user_id,)).rowcount
        c.execute("DELETE FROM users WHERE id=?", (user_id,))

    pseudo = "erased:" + hashlib.sha256(email.lower().encode()).hexdigest()[:10]
    consents = _lines(models.CONSENT_PATH)
    kept = [r for r in consents if r.get("user_id") != email]
    if len(kept) != len(consents):
        _rewrite(models.CONSENT_PATH, kept)
    reqs = _lines(models.REQUESTS_PATH)
    pseudonymised = 0
    for r in reqs:
        if r.get("user_id") == email:
            r["user_id"], r["notes"] = pseudo, ""
            pseudonymised += 1
    if pseudonymised:
        _rewrite(models.REQUESTS_PATH, reqs)
    removed_subs = [s.id for s in subs.list_all() if s.email == email.lower()]
    for sid in removed_subs:
        subs.remove(sid)
    return {"user_id": user_id, "sessions_deleted": sessions, "consents_deleted": len(consents) - len(kept),
            "requests_pseudonymised": pseudonymised, "subscriptions_deleted": len(removed_subs)}

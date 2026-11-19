"""Identité de l'appelant (P-083) : une personne, une méthode, éventuellement une clé.

- `session`    : connexion e-mail + mot de passe (Bearer). Seule méthode admise pour résoudre / revoir / valider.
- `api_key`    : clé personnelle `mzb_…` ; un seul propriétaire ; rôle relu à CHAQUE requête depuis l'utilisateur.
- `legacy_key` : clé partagée des variables d'environnement. Non attribuable à une personne, échéance ferme (voir `legacy_keys`).
Le contexte est posé par `RequireRole` et lu par le journal d'audit : chaque événement dit qui, comment et avec quelle clé.
"""
from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass


@dataclass(frozen=True)
class Identity:
    method: str                    # "session" | "api_key" | "legacy_key"
    role: str                      # rôle EFFECTIF (une clé héritée en lecture seule vaut « viewer »)
    user_id: int | None = None
    key_id: int | None = None
    key_ref: str | None = None     # préfixe non secret (clé personnelle) ou empreinte courte (clé héritée)
    configured_role: str | None = None   # rôle configuré d'une clé héritée avant plafonnement

    @property
    def actor(self) -> str:
        if self.method == "legacy_key":
            return f"legacy:{self.configured_role or self.role}:{self.key_ref}"      # explicitement non attribuable
        return f"user:{self.user_id}"

    def audit_details(self) -> dict:
        d: dict = {"auth_method": self.method}
        if self.key_id is not None:
            d["key_id"] = self.key_id
        if self.key_ref:
            d["key_ref"] = self.key_ref
        return d


current_identity: ContextVar[Identity | None] = ContextVar("current_identity", default=None)


class ApiKeyRejected(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status, self.message = status, message

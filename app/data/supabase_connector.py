"""Connecteur Supabase via PostgREST (lecture seule).

Utilisation : URL et clé anon passées explicitement ou via SUPABASE_URL / SUPABASE_ANON_KEY.
Circuit breaker : 3 échecs consécutifs → pause 60 s.
Sécurité : URL doit commencer par le schéma sécurisé (https), clé JWT-like, noms de table alphanumériques.
"""
from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field
from typing import Any

import httpx
import pandas as pd

_TIMEOUT = 20.0
_CB_MAX_FAILURES = 3
_CB_RESET_SECONDS = 60
_DEFAULT_LIMIT = 5_000
_MAX_LIMIT = 20_000

_TABLE_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]{0,127}$")
_JWT_RE = re.compile(r"^eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]*$")


def _validate_url(url: str) -> str:
    """Refuse les URLs non-HTTPS pour éviter le SSRF vers des services internes."""
    u = url.strip().rstrip("/")
    if not u.startswith("https://"):
        raise ValueError("SUPABASE_URL doit commencer par https://")
    return u


def _validate_key(key: str) -> str:
    """Refuse les clés qui ne ressemblent pas à un JWT Supabase."""
    k = key.strip()
    if not _JWT_RE.match(k):
        raise ValueError("SUPABASE_ANON_KEY doit être un JWT (eyJ…)")
    return k


def _validate_table(table: str) -> str:
    if not _TABLE_RE.match(table):
        raise ValueError(f"Nom de table invalide : {table!r}. Alphanumérique + _ uniquement.")
    return table


@dataclass
class _CircuitBreaker:
    failures: int = 0
    open_until: float = 0.0

    def record_success(self) -> None:
        self.failures = 0
        self.open_until = 0.0

    def record_failure(self) -> None:
        self.failures += 1
        if self.failures >= _CB_MAX_FAILURES:
            self.open_until = time.monotonic() + _CB_RESET_SECONDS

    @property
    def is_open(self) -> bool:
        if self.open_until and time.monotonic() < self.open_until:
            return True
        if self.open_until and time.monotonic() >= self.open_until:
            self.failures = 0
            self.open_until = 0.0
        return False


class SupabaseConnector:
    """Client PostgREST léger pour Supabase.

    Paramètres : url et anon_key passés explicitement ou via variables d'environnement.
    """

    def __init__(self, url: str | None = None, anon_key: str | None = None) -> None:
        raw_url = url or os.environ.get("SUPABASE_URL", "")
        raw_key = anon_key or os.environ.get("SUPABASE_ANON_KEY", "")
        if not raw_url:
            raise EnvironmentError(
                "URL Supabase manquante. Passer url= ou définir SUPABASE_URL."
            )
        if not raw_key:
            raise EnvironmentError(
                "Clé anon Supabase manquante. Passer anon_key= ou définir SUPABASE_ANON_KEY."
            )
        self._base = _validate_url(raw_url)
        self._key = _validate_key(raw_key)
        self._cb = _CircuitBreaker()

    def _headers(self) -> dict[str, str]:
        return {
            "apikey": self._key,
            "Authorization": f"Bearer {self._key}",
            "Accept": "application/json",
        }

    def _get(self, path: str, params: dict | None = None) -> Any:
        if self._cb.is_open:
            raise RuntimeError("Supabase circuit breaker ouvert — trop d'échecs consécutifs.")
        url = f"{self._base}/rest/v1{path}"
        try:
            resp = httpx.get(url, headers=self._headers(), params=params, timeout=_TIMEOUT)
            resp.raise_for_status()
            self._cb.record_success()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            self._cb.record_failure()
            raise RuntimeError(f"Supabase HTTP {exc.response.status_code} : {exc.response.text[:200]}") from exc
        except httpx.RequestError as exc:
            self._cb.record_failure()
            raise RuntimeError(f"Erreur réseau Supabase : {exc}") from exc

    def list_tables(self) -> list[str]:
        """Découvre les tables exposées via l'API OpenAPI de PostgREST.

        Retourne uniquement les tables (paths de la forme /{table}).
        """
        data = self._get("/")
        paths: dict = data.get("paths", {})
        tables: list[str] = []
        for path in paths:
            if path.startswith("/") and path.count("/") == 1:
                name = path.lstrip("/")
                if _TABLE_RE.match(name):
                    tables.append(name)
        return sorted(tables)

    def load_table(self, table: str, limit: int = _DEFAULT_LIMIT) -> pd.DataFrame:
        """Charge une table Supabase dans un DataFrame pandas.

        limit est plafonné à MAX_LIMIT pour éviter les requêtes trop volumineuses.
        """
        _validate_table(table)
        effective_limit = min(max(1, limit), _MAX_LIMIT)
        rows = self._get(f"/{table}", params={"select": "*", "limit": str(effective_limit)})
        if not isinstance(rows, list):
            raise RuntimeError(f"Réponse inattendue de Supabase pour la table {table!r}.")
        return pd.DataFrame(rows)

    def test_connection(self) -> bool:
        """Vérifie que la connexion est valide en appelant l'endpoint racine."""
        try:
            self._get("/")
            return True
        except RuntimeError:
            return False

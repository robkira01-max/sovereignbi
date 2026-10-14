"""HDX (Humanitarian Data Exchange) CKAN API client.

Uses the OCHA HDX CKAN REST API to search and download datasets.
Circuit breaker: 3 consecutive failures → disabled for 60 s.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any

import httpx
import pandas as pd

from app.data.hxl_parser import read_hxl_csv

_DEFAULT_BASE = "https://data.humdata.org"
_TIMEOUT = 15.0
_CB_MAX_FAILURES = 3
_CB_RESET_SECONDS = 60


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


class HdxClient:
    """Lightweight HDX CKAN client."""

    def __init__(self, base_url: str | None = None) -> None:
        raw = base_url or os.environ.get("SOVEREIGN_HDX_URL", _DEFAULT_BASE)
        self._base = raw.rstrip("/")
        self._cb = _CircuitBreaker()

    def _get(self, path: str, params: dict | None = None) -> Any:
        if self._cb.is_open:
            raise RuntimeError("HDX circuit breaker open — trop d'échecs consécutifs.")
        url = f"{self._base}{path}"
        try:
            resp = httpx.get(url, params=params or {}, timeout=_TIMEOUT)
            resp.raise_for_status()
            self._cb.record_success()
            return resp.json()
        except Exception as exc:
            self._cb.record_failure()
            raise RuntimeError(f"HDX API error: {exc}") from exc

    def search_datasets(
        self,
        query: str,
        org: str | None = None,
        limit: int = 20,
        start: int = 0,
    ) -> list[dict]:
        """Search datasets on HDX. Returns list of dataset metadata dicts."""
        fq = f'organization:"{org}"' if org else ""
        data = self._get(
            "/api/3/action/package_search",
            params={
                "q": query,
                "fq": fq,
                "rows": min(limit, 100),
                "start": start,
            },
        )
        return data.get("result", {}).get("results", [])

    def get_resource_url(self, dataset_id: str, resource_index: int = 0) -> str:
        """Return the download URL of a specific resource within a dataset."""
        data = self._get(
            "/api/3/action/package_show",
            params={"id": dataset_id},
        )
        resources: list[dict] = data.get("result", {}).get("resources", [])
        if not resources:
            raise ValueError(f"Dataset {dataset_id!r} has no resources.")
        if resource_index >= len(resources):
            raise IndexError(
                f"Dataset {dataset_id!r} only has {len(resources)} resource(s)."
            )
        url = resources[resource_index].get("url", "")
        if not url:
            raise ValueError(f"Resource {resource_index} has no download URL.")
        return url

    def download_csv(
        self,
        url: str,
        strip_hxl: bool = True,
    ) -> pd.DataFrame:
        """Download a CSV from HDX and optionally strip the HXL hashtag row."""
        if self._cb.is_open:
            raise RuntimeError("HDX circuit breaker open.")
        try:
            resp = httpx.get(url, timeout=30.0, follow_redirects=True)
            resp.raise_for_status()
            self._cb.record_success()
        except Exception as exc:
            self._cb.record_failure()
            raise RuntimeError(f"Échec téléchargement HDX : {exc}") from exc

        if strip_hxl:
            df, _ = read_hxl_csv(resp.text)
            return df
        import io
        return pd.read_csv(io.StringIO(resp.text), dtype=str, keep_default_na=False)

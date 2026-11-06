"""Client NISR — National Institute of Statistics of Rwanda (portail CKAN).

Licence des données : Rwanda Open Data Policy (CC-BY compatible).
Chaque dataset est vérifié individuellement (champ `license_id`).

Sécurité : même garanties que KNBSClient (SSRF guard, circuit breaker).
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from io import StringIO
from typing import Any

import httpx
import pandas as pd

# ── Constants ────────────────────────────────────────────────────────────────

_BASE_URL = "https://www.statistics.gov.rw/api/3/action"
_TIMEOUT  = 20.0
_CB_MAX   = 3
_CB_RESET = 60

# Rwanda Open Data Policy licences permises
_OPEN_LICENCES = {
    "odc-pddl", "odc-odbl", "odc-by",
    "cc-zero", "cc-by", "cc-by-sa",
    "rwanda-open-data",         # Rwanda Open Data Policy
    "notspecified",             # traité comme ouvert sauf mention contraire NISR
}

_ID_RE  = re.compile(r"^[a-zA-Z0-9_\-]{1,128}$")
_URL_RE = re.compile(r"^https://")

# ── Helpers ──────────────────────────────────────────────────────────────────

def _safe_url(url: str) -> str:
    u = url.strip()
    if not _URL_RE.match(u):
        raise ValueError(f"URL refusée (non-HTTPS) : {u!r}")
    return u


def _safe_id(value: str, label: str = "id") -> str:
    if not _ID_RE.match(value):
        raise ValueError(f"{label} invalide : {value!r}")
    return value


# ── Circuit breaker ──────────────────────────────────────────────────────────

@dataclass
class _CircuitBreaker:
    failures: int = 0
    open_until: float = 0.0

    def is_open(self) -> bool:
        return time.time() < self.open_until

    def record_success(self) -> None:
        self.failures = 0
        self.open_until = 0.0

    def record_failure(self) -> None:
        self.failures += 1
        if self.failures >= _CB_MAX:
            self.open_until = time.time() + _CB_RESET

    def check(self) -> None:
        if self.is_open():
            raise RuntimeError(
                f"NISR circuit breaker ouvert — réessai dans "
                f"{int(self.open_until - time.time())} s"
            )


# ── Dataset record ───────────────────────────────────────────────────────────

@dataclass
class NISRDataset:
    id: str
    name: str
    title: str
    license_id: str
    license_title: str
    resources: list[dict[str, Any]] = field(default_factory=list)

    @property
    def is_permitted(self) -> bool:
        return self.license_id.lower() in _OPEN_LICENCES

    @property
    def license_reason(self) -> str:
        return (
            f"Licence '{self.license_id}' permise"
            if self.is_permitted
            else f"Licence '{self.license_id}' non autorisée — ingestion refusée"
        )


# ── Client ───────────────────────────────────────────────────────────────────

class NISRClient:
    """Client CKAN léger pour le portail statistique du Rwanda (NISR)."""

    def __init__(
        self,
        base_url: str = _BASE_URL,
        timeout: float = _TIMEOUT,
    ) -> None:
        self._base = _safe_url(base_url.rstrip("/"))
        self._timeout = timeout
        self._cb = _CircuitBreaker()

    def _get(self, action: str, params: dict[str, Any] | None = None) -> Any:
        self._cb.check()
        url = f"{self._base}/{action}"
        try:
            resp = httpx.get(url, params=params, timeout=self._timeout)
            resp.raise_for_status()
            data = resp.json()
            if not data.get("success"):
                raise ValueError(f"CKAN error: {data.get('error')}")
            self._cb.record_success()
            return data["result"]
        except Exception:
            self._cb.record_failure()
            raise

    def search_datasets(self, q: str, rows: int = 20) -> list[NISRDataset]:
        result = self._get("package_search", {"q": q, "rows": min(rows, 100)})
        datasets = []
        for pkg in result.get("results", []):
            datasets.append(NISRDataset(
                id=pkg.get("id", ""),
                name=pkg.get("name", ""),
                title=pkg.get("title", ""),
                license_id=pkg.get("license_id", "notspecified"),
                license_title=pkg.get("license_title", ""),
                resources=pkg.get("resources", []),
            ))
        return datasets

    def get_dataset(self, dataset_id: str) -> NISRDataset:
        _safe_id(dataset_id, "dataset_id")
        pkg = self._get("package_show", {"id": dataset_id})
        return NISRDataset(
            id=pkg.get("id", ""),
            name=pkg.get("name", ""),
            title=pkg.get("title", ""),
            license_id=pkg.get("license_id", "notspecified"),
            license_title=pkg.get("license_title", ""),
            resources=pkg.get("resources", []),
        )

    def fetch_csv(self, resource_url: str, max_rows: int = 50_000) -> pd.DataFrame:
        url = _safe_url(resource_url)
        self._cb.check()
        try:
            resp = httpx.get(url, timeout=self._timeout, follow_redirects=True)
            resp.raise_for_status()
            self._cb.record_success()
        except Exception:
            self._cb.record_failure()
            raise
        df = pd.read_csv(StringIO(resp.text))
        if len(df) > max_rows:
            df = df.iloc[:max_rows]
        return df

    def fetch_dataset_first_csv(
        self, dataset_id: str, max_rows: int = 50_000
    ) -> tuple[NISRDataset, pd.DataFrame]:
        ds = self.get_dataset(dataset_id)
        if not ds.is_permitted:
            raise PermissionError(ds.license_reason)
        csv_resources = [
            r for r in ds.resources
            if r.get("format", "").upper() in ("CSV", "TEXT/CSV")
            and r.get("url", "").startswith("https://")
        ]
        if not csv_resources:
            raise ValueError(
                f"Aucune ressource CSV https:// trouvée dans le dataset '{dataset_id}'."
            )
        url = csv_resources[0]["url"]
        df = self.fetch_csv(url, max_rows=max_rows)
        return ds, df

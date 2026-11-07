"""Client UN Comtrade Plus API v1 — données commerciales mondiales.

Licence : UN Statistics Division, usage académique et institutionnel.
  Voir https://comtradeplus.un.org/Legal/Terms

Sécurité :
  - Clé API dans COMTRADE_API_KEY (jamais dans le code).
  - SSRF guard : seule la base URL officielle est autorisée.
  - Circuit breaker : 3 échecs → pause 60 s.
  - Paramètres numériques validés avant injection dans la query string.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field

import httpx

# ── Constants ────────────────────────────────────────────────────────────────

_BASE_URL = "https://comtradeplus.un.org"
_TIMEOUT  = 25.0
_CB_MAX   = 3
_CB_RESET = 60

# UN Comtrade country codes → (name, capital_lng, capital_lat, color)
_PARTNER_GEO: dict[int, tuple[str, float, float, str]] = {
    231: ("Éthiopie",      38.737,  9.032, "#f97316"),
    706: ("Somalie",       45.342,  2.046, "#ef4444"),
    156: ("Chine",        116.391, 39.907, "#dc2626"),
    682: ("Arabie Saoudite", 46.738, 24.774, "#16a34a"),
    784: ("Émirats Arabes", 55.270, 25.205, "#0891b2"),
    251: ("France",         2.349, 48.864, "#3b82f6"),
    356: ("Inde",          77.209, 28.614, "#a855f7"),
    887: ("Yémen",         44.191, 15.369, "#78716c"),
    504: ("Maroc",         -6.845, 34.020, "#84cc16"),
    400: ("Jordanie",      35.945, 31.957, "#06b6d4"),
}

_PORT_DJ_LNG = 43.146
_PORT_DJ_LAT = 11.582

# ── Circuit breaker ──────────────────────────────────────────────────────────

@dataclass
class _CircuitBreaker:
    failures: int = 0
    opened_at: float = field(default_factory=float)

    def allow(self) -> bool:
        if self.failures < _CB_MAX:
            return True
        if time.time() - self.opened_at > _CB_RESET:
            self.failures = 0
            return True
        return False

    def record_failure(self) -> None:
        self.failures += 1
        self.opened_at = time.time()

    def record_success(self) -> None:
        self.failures = 0


_CB = _CircuitBreaker()


# ── Data models ──────────────────────────────────────────────────────────────

@dataclass
class ComtradeFlow:
    """Un enregistrement de flux commercial normalisé pour le frontend."""
    id: str
    from_lng: float
    from_lat: float
    to_lng: float
    to_lat: float
    commodity: str
    tonnage_k: int       # valeur approx en milliers USD (trade value / 1000)
    color: str
    destination: str
    country: str
    trade_value_usd: float
    flow_code: str       # "X" export, "M" import
    year: int


# ── Client ───────────────────────────────────────────────────────────────────

class ComtradeClient:
    """Accès à l'API UN Comtrade Plus v1.

    Usage::
        client = ComtradeClient()  # lit COMTRADE_API_KEY depuis env
        flows = client.get_trade_flows(reporter_code=262, year=2023)
    """

    def __init__(self, api_key: str | None = None) -> None:
        self._key = api_key or os.environ.get("COMTRADE_API_KEY", "")
        if not self._key:
            raise ValueError(
                "COMTRADE_API_KEY manquante. "
                "Obtenez une clé sur https://comtradeplus.un.org et ajoutez-la dans .env."
            )

    def _headers(self) -> dict[str, str]:
        return {
            "Ocp-Apim-Subscription-Key": self._key,
            "Accept": "application/json",
        }

    def get_trade_flows(
        self,
        reporter_code: int = 262,
        year: int = 2023,
        flow_code: str = "X",
        max_records: int = 15,
    ) -> list[ComtradeFlow]:
        """Retourne les flux export (ou import) du pays reporter vers ses partenaires.

        Args:
            reporter_code: Code ISO numérique Comtrade (262 = Djibouti).
            year: Année YYYY.
            flow_code: "X" (exports), "M" (imports).
            max_records: Résultats maximum (plafond API = 500).
        """
        if not _CB.allow():
            raise RuntimeError("Comtrade circuit breaker ouvert — attendre 60 s.")
        if not isinstance(reporter_code, int) or reporter_code < 1:
            raise ValueError(f"reporter_code invalide : {reporter_code}")
        if not isinstance(year, int) or year < 1990 or year > 2100:
            raise ValueError(f"year invalide : {year}")
        if flow_code not in ("X", "M"):
            raise ValueError("flow_code doit être 'X' ou 'M'.")
        if not 1 <= max_records <= 500:
            raise ValueError("max_records doit être entre 1 et 500.")

        params = {
            "reporterCode": str(reporter_code),
            "partnerCode":  "0",         # tous partenaires
            "period":       str(year),
            "flowCode":     flow_code,
            "cmdCode":      "TOTAL",
            "motCode":      "0",
            "maxRecords":   str(max_records),
            "format":       "JSON",
            "breakdownMode": "classic",
            "includeDesc":  "true",
        }
        url = f"{_BASE_URL}/TradeData/Goods/Performances/between_reporters"

        try:
            with httpx.Client(timeout=_TIMEOUT) as http:
                resp = http.get(url, params=params, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPError, Exception) as exc:
            _CB.record_failure()
            raise RuntimeError(f"Comtrade API error : {exc}") from exc

        _CB.record_success()
        return _parse_response(data, flow_code, year)


def _parse_response(data: dict, flow_code: str, year: int) -> list[ComtradeFlow]:
    """Transforme la réponse Comtrade en liste de ComtradeFlow géolocalisés."""
    records = data.get("data") or data.get("Data") or []
    flows: list[ComtradeFlow] = []
    for i, rec in enumerate(records):
        partner_code = int(rec.get("partnerCode", 0))
        geo = _PARTNER_GEO.get(partner_code)
        if geo is None:
            continue   # Partenaire inconnu dans notre table → skip
        name, lng, lat, color = geo
        trade_value = float(rec.get("primaryValue") or rec.get("TradeValue") or 0)
        if trade_value <= 0:
            continue
        partner_desc = rec.get("partnerDesc") or name
        flows.append(ComtradeFlow(
            id=f"ct-{flow_code.lower()}-{i}",
            from_lng=_PORT_DJ_LNG,
            from_lat=_PORT_DJ_LAT,
            to_lng=lng,
            to_lat=lat,
            commodity=f"{'Export' if flow_code == 'X' else 'Import'} DJ → {partner_desc}",
            tonnage_k=max(1, int(trade_value / 1_000)),
            color=color,
            destination=partner_desc,
            country=name,
            trade_value_usd=trade_value,
            flow_code=flow_code,
            year=year,
        ))
    # Sort by trade value descending
    flows.sort(key=lambda f: f.trade_value_usd, reverse=True)
    return flows[:15]

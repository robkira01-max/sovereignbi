"""Flux commerciaux Port de Djibouti.

Si COMTRADE_API_KEY est définie, les données sont récupérées en temps réel
depuis l'API UN Comtrade Plus v1. Sinon, des données illustratives sont retournées
(suffisantes pour la démo et les tests).
"""
from __future__ import annotations

import os

from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/trade-flows", tags=["trade-flows"])


class TradeFlowItem(BaseModel):
    id: str
    from_lng: float
    from_lat: float
    to_lng: float
    to_lat: float
    commodity: str
    tonnage_k: int
    color: str
    destination: str
    country: str
    # Champs enrichis (nuls en mode démo)
    trade_value_usd: float = 0.0
    flow_code: str = "X"
    year: int = 0
    source: str = "demo"


_PORT_DJ_LNG = 43.146
_PORT_DJ_LAT = 11.582

_DEMO_FLOWS: list[TradeFlowItem] = [
    TradeFlowItem(
        id="f1", from_lng=_PORT_DJ_LNG, from_lat=_PORT_DJ_LAT,
        to_lng=38.737, to_lat=9.032,
        commodity="Céréales & denrées", tonnage_k=2800,
        color="#f97316", destination="Addis-Abeba", country="Éthiopie",
    ),
    TradeFlowItem(
        id="f2", from_lng=_PORT_DJ_LNG, from_lat=_PORT_DJ_LAT,
        to_lng=41.862, to_lat=9.596,
        commodity="Carburant & énergie", tonnage_k=1900,
        color="#ef4444", destination="Dire Dawa", country="Éthiopie",
    ),
    TradeFlowItem(
        id="f3", from_lng=_PORT_DJ_LNG, from_lat=_PORT_DJ_LAT,
        to_lng=39.475, to_lat=13.490,
        commodity="Engrais agricoles", tonnage_k=950,
        color="#22c55e", destination="Mekele", country="Éthiopie",
    ),
    TradeFlowItem(
        id="f4", from_lng=_PORT_DJ_LNG, from_lat=_PORT_DJ_LAT,
        to_lng=39.634, to_lat=11.130,
        commodity="Équipements industriels", tonnage_k=620,
        color="#3b82f6", destination="Dessie", country="Éthiopie",
    ),
    TradeFlowItem(
        id="f5", from_lng=_PORT_DJ_LNG, from_lat=_PORT_DJ_LAT,
        to_lng=37.456, to_lat=7.051,
        commodity="Biens de consommation", tonnage_k=480,
        color="#a855f7", destination="Hawassa", country="Éthiopie",
    ),
]


@router.get("", response_model=list[TradeFlowItem], summary="Flux commerciaux Port de Djibouti")
async def get_trade_flows(
    year: int = Query(2023, ge=1990, le=2100, description="Année Comtrade"),
    flow: str = Query("X", description="'X' exports, 'M' imports"),
) -> list[TradeFlowItem]:
    """Retourne les flux commerciaux du Port de Djibouti.

    Si COMTRADE_API_KEY est définie, données Comtrade Plus réelles.
    Sinon, données illustratives (démo).
    """
    if flow not in ("X", "M"):
        flow = "X"

    api_key = os.environ.get("COMTRADE_API_KEY", "").strip()
    if api_key:
        try:
            from app.data.comtrade_client import ComtradeClient
            client = ComtradeClient(api_key=api_key)
            live = client.get_trade_flows(reporter_code=262, year=year, flow_code=flow)
            return [
                TradeFlowItem(
                    id=f.id,
                    from_lng=f.from_lng, from_lat=f.from_lat,
                    to_lng=f.to_lng, to_lat=f.to_lat,
                    commodity=f.commodity,
                    tonnage_k=f.tonnage_k,
                    color=f.color,
                    destination=f.destination,
                    country=f.country,
                    trade_value_usd=f.trade_value_usd,
                    flow_code=f.flow_code,
                    year=f.year,
                    source="comtrade",
                )
                for f in live
            ]
        except Exception:
            # Fallback to demo data — do not let API errors break the UI
            pass

    return _DEMO_FLOWS

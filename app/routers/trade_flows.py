"""Flux commerciaux Port de Djibouti — données synthétiques illustratives."""
from __future__ import annotations

from fastapi import APIRouter
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


_PORT_DJ_LNG = 43.146
_PORT_DJ_LAT = 11.582

_FLOWS: list[TradeFlowItem] = [
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
async def get_trade_flows() -> list[TradeFlowItem]:
    """Retourne les flux commerciaux synthétiques du Port de Djibouti.

    Données illustratives uniquement — ne pas utiliser comme source officielle.
    """
    return _FLOWS

"""GET /cities endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Request

from ..dependencies import AppState
from ..schemas import CitiesResponse, CityBonusSchema, CitySchema

router = APIRouter(prefix="/cities", tags=["cities"])


@router.get("", response_model=CitiesResponse)
def list_cities(request: Request) -> CitiesResponse:
    state: AppState = request.app.state.app_state
    cities: list[CitySchema] = []
    for city_name, categories in state.city_bonuses.items():
        bonuses = [
            CityBonusSchema(category=cat, bonus_pct=round(rate * 100, 1))
            for cat, rate in categories.items()
        ]
        cities.append(CitySchema(name=city_name, bonuses=bonuses))
    cities.sort(key=lambda c: c.name)
    return CitiesResponse(cities=cities)

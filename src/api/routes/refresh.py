"""Manual price refresh endpoint."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(tags=["refresh"])
logger = logging.getLogger(__name__)


class RefreshResponse(BaseModel):
    status: str
    prices_count: int


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_prices(request: Request) -> RefreshResponse:
    """Trigger an immediate price refresh (fetches fresh data from Albion API)."""
    from ...albion_client import AlbionAPIClient, PRD_CITY_LOCATIONS

    state = request.app.state.app_state

    client = AlbionAPIClient()
    try:
        all_item_ids: list[str] = sorted({r.product_id for r in state.recipes})
        for r in state.recipes:
            for m in r.materials:
                all_item_ids.append(m.item_id)
        all_item_ids = sorted(set(all_item_ids))

        prices = await client.get_prices_async(all_item_ids, PRD_CITY_LOCATIONS, 1)
        state.prices = prices
        state.cache.invalidate_all()
        logger.info("Manual refresh: %d price entries", len(prices))
    finally:
        client.close()

    return RefreshResponse(status="ok", prices_count=len(prices))

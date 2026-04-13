"""FastAPI app factory with lifespan and CORS middleware."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .dependencies import AppState
from .routes import api_router

logger = logging.getLogger(__name__)

# Paths resolved relative to project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_ITEMS_JSON = _PROJECT_ROOT / "data" / "items.json"


async def _refresh_prices(state: AppState, interval: float = 300.0) -> None:
    """Background task: refresh prices from Albion API every `interval` seconds."""
    from ..albion_client import AlbionAPIClient

    while True:
        try:
            client = AlbionAPIClient()
            try:
                all_item_ids = sorted({r.product_id for r in state.recipes})
                for r in state.recipes:
                    for m in r.materials:
                        all_item_ids.append(m.item_id)
                all_item_ids = sorted(set(all_item_ids))

                from ..albion_client import PRD_CITY_LOCATIONS

                prices = await asyncio.to_thread(
                    client.get_prices, all_item_ids, PRD_CITY_LOCATIONS, 1
                )
                state.prices = prices
                state.cache.invalidate_all()
                logger.info("Prices refreshed: %d entries", len(prices))
            finally:
                client.close()
        except Exception:
            logger.exception("Failed to refresh prices")
        await asyncio.sleep(interval)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup: load recipes + initial prices. Shutdown: cancel background tasks."""
    state: AppState = app.state.app_state

    # Load recipes if items.json exists
    if _DEFAULT_ITEMS_JSON.exists():
        from ..recipe_parser import parse_items_json

        state.recipes = parse_items_json(_DEFAULT_ITEMS_JSON)
        state.build_recipe_index()
        logger.info("Loaded %d recipes from items.json", len(state.recipes))

    # Fetch initial prices (lazy — don't block startup if API is slow)
    refresh_task = asyncio.create_task(_refresh_prices(state, interval=300.0))
    try:
        yield
    finally:
        refresh_task.cancel()
        try:
            await refresh_task
        except asyncio.CancelledError:
            pass


def create_app(state: AppState | None = None) -> FastAPI:
    """Application factory.

    Parameters
    ----------
    state:
        Optional pre-configured AppState (useful for testing).
    """
    app_state = state or AppState()

    app = FastAPI(
        title="Albion Craft Ranker API",
        version="2.0.0",
        lifespan=lifespan,
    )
    app.state.app_state = app_state

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)
    return app

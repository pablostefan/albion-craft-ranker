"""FastAPI app factory with lifespan and CORS middleware."""
from __future__ import annotations

import asyncio
import logging
import os
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


async def _load_prices_once(state: AppState) -> None:
    """Fetch prices from Albion API once and update state."""
    from ..albion_client import AlbionAPIClient, PRD_CITY_LOCATIONS

    client = AlbionAPIClient()
    try:
        all_item_ids = sorted({r.product_id for r in state.recipes})
        for r in state.recipes:
            for m in r.materials:
                all_item_ids.append(m.item_id)
        all_item_ids = sorted(set(all_item_ids))
        prices = await client.get_prices_async(all_item_ids, PRD_CITY_LOCATIONS, 1)
        state.prices = prices
        state.cache.invalidate_all()
        logger.info("Prices refreshed: %d entries", len(prices))
    finally:
        client.close()


async def _refresh_prices(state: AppState, interval: float = 300.0) -> None:
    """Background task: refresh prices from Albion API every `interval` seconds."""
    while True:
        try:
            await _load_prices_once(state)
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

    # Background loop: fetches prices immediately on first run, then every 300s.
    # Uses async concurrent requests (~20-30s for ~9k IDs) instead of sequential (~200s).
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
        allow_origins=os.getenv(
            "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
        ).split(","),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)

    @app.get("/health", tags=["health"])
    async def health_check() -> dict:
        """Liveness probe for Render health check."""
        return {"status": "ok"}

    return app

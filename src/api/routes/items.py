"""GET /items and GET /items/{item_id} endpoints."""
from __future__ import annotations

from dataclasses import replace as _replace
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ...albion_client import AlbionAPIClient, PRD_CITY_LOCATIONS
from ...models import ScoredItem
from ...scoring import _chunk, _extract_daily_volume, rank_items_v2
from ..dependencies import AppState
from ..schemas import (
    CityComparison,
    ItemDetailResponse,
    ItemsResponse,
    MaterialCost,
    ScoredItemSchema,
)

router = APIRouter(prefix="/items", tags=["items"])

VALID_SORT_FIELDS = {"final_score", "return_rate_pct", "profit", "profit_per_focus", "daily_volume"}
VALID_MARKETS = {"marketplace", "black_market", "comparison"}


def _get_state(request: Request) -> AppState:
    return request.app.state.app_state


def _scored_items(
    state: AppState, city: str, market: str, sort_by: str, *, sell_city: str | None = None, config_override: object | None = None, exclude_cities: frozenset[str] = frozenset(), use_focus: bool = False,
) -> list[ScoredItem]:
    use_cache = config_override is None
    cfg = config_override if config_override is not None else state.config

    if use_cache:
        cache_key = (city, market, sort_by, sell_city, exclude_cities, use_focus)
        cached = state.cache.get(cache_key)
        if cached is not None:
            return cached

    items = rank_items_v2(
        state.recipes,
        state.prices,
        state.city_bonuses,
        cfg,
        craft_city=city,
        sell_mode=market,
        sell_city=sell_city,
        exclude_cities=exclude_cities,
        use_focus=use_focus,
    )

    # rank_items_v2 already returns items sorted by final_score descending.
    if sort_by == "final_score":
        pass
    elif sort_by == "profit":
        items.sort(key=lambda x: x.profit_absolute, reverse=True)
    elif sort_by == "profit_per_focus":
        items.sort(key=lambda x: x.profit_per_focus, reverse=True)
    # default: return_rate_pct → already sorted by final_score which correlates

    if use_cache:
        state.cache.set(cache_key, items)
    return items


@router.get("", response_model=ItemsResponse)
def list_items(
    request: Request,
    city: str = Query("Lymhurst"),
    category: str | None = Query(None),
    tier: int | None = Query(None),
    enchantment: int | None = Query(None),
    quality: int | None = Query(None),
    market: str = Query("marketplace"),
    sell_city: str | None = Query(None, description="City where items are sold (for cross-city arbitrage)"),
    exclude_cities: str | None = Query(None, description="Comma-separated cities to exclude from best-city calculation"),
    sort_by: str = Query("daily_volume"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    min_profit: float | None = Query(None),
    w_profit: float | None = Query(None, ge=0, le=1),
    w_focus: float | None = Query(None, ge=0, le=1),
    w_volume: float | None = Query(None, ge=0, le=1),
    w_freshness: float | None = Query(None, ge=0, le=1),
    use_focus: bool = Query(False, description="Whether to include focus cost in profit calculations"),
) -> ItemsResponse:
    state = _get_state(request)

    excluded = frozenset(c.strip() for c in exclude_cities.split(",") if c.strip()) if exclude_cities else frozenset()

    # Per-request scoring config override when custom weights are provided
    custom_weights = [w_profit, w_focus, w_volume, w_freshness]
    if any(w is not None for w in custom_weights):
        config_override = _replace(
            state.config,
            profit_weight=w_profit if w_profit is not None else state.config.profit_weight,
            focus_weight=w_focus if w_focus is not None else state.config.focus_weight,
            volume_weight=w_volume if w_volume is not None else state.config.volume_weight,
            freshness_weight=w_freshness if w_freshness is not None else state.config.freshness_weight,
        )
    else:
        config_override = None

    if market not in VALID_MARKETS:
        raise HTTPException(400, f"Invalid market: {market}")
    if sort_by not in VALID_SORT_FIELDS:
        raise HTTPException(400, f"Invalid sort_by: {sort_by}")

    items = _scored_items(state, city, market, sort_by, sell_city=sell_city, config_override=config_override, exclude_cities=excluded, use_focus=use_focus)

    # Apply filters
    filtered = items
    if category:
        filtered = [i for i in filtered if i.product_id and _matches_category(i, category, state)]
    else:
        # When no category is selected, exclude artefacts
        filtered = [i for i in filtered if i.product_id and _matches_category(i, "artefacts", state) is False]
    if tier is not None:
        filtered = [i for i in filtered if _matches_tier(i, tier, state)]
    if enchantment is not None:
        filtered = [i for i in filtered if _matches_enchantment(i, enchantment, state)]
    if min_profit is not None:
        filtered = [i for i in filtered if i.profit_absolute >= min_profit]

    # Re-sort after filtering
    descending = order == "desc"

    # Helper: fetch daily volumes via history API for a list of items
    def _fetch_volumes(item_list: list[ScoredItem]) -> dict[str, float | None]:
        vols: dict[str, float | None] = {}
        if not item_list:
            return vols
        try:
            sell_location = "Black Market" if market == "black_market" else city
            client = AlbionAPIClient()
            all_ids = [i.product_id for i in item_list]
            for batch in _chunk(all_ids, 100):
                history = client.get_history_bulk(batch, sell_location, quality=1, days=7)
                for pid in batch:
                    rows = history.get(pid, [])
                    data_points: list[dict] = []
                    for row in rows:
                        data_points.extend(row.get("data", []))
                    vols[pid] = _extract_daily_volume(data_points) if data_points else None
            client.close()
        except Exception:
            pass
        return vols

    # When sorting by daily_volume, fetch volumes for ALL filtered items first
    volumes: dict[str, float | None] = {}
    if sort_by == "daily_volume":
        volumes = _fetch_volumes(filtered)
        filtered.sort(key=lambda x: volumes.get(x.product_id) or 0.0, reverse=descending)
    elif sort_by == "profit":
        filtered.sort(key=lambda x: x.profit_absolute, reverse=descending)
    elif sort_by == "final_score":
        volumes = _fetch_volumes(filtered)
        filtered.sort(
            key=lambda x: ((volumes.get(x.product_id) or 0) > 0, x.final_score),
            reverse=descending,
        )
    elif sort_by == "profit_per_focus":
        filtered.sort(key=lambda x: x.profit_per_focus, reverse=descending)
    else:
        filtered.sort(key=lambda x: x.return_rate_pct, reverse=descending)

    total = len(filtered)
    page = filtered[offset: offset + limit]

    # For non-volume sorts, fetch volumes only for the current page
    if sort_by not in ("daily_volume", "final_score"):
        volumes = _fetch_volumes(page)

    return ItemsResponse(
        items=[ScoredItemSchema(**{**_item_dict(i), "daily_volume": volumes.get(i.product_id)}) for i in page],
        total=total,
        filters_applied={
            "city": city,
            "category": category,
            "tier": tier,
            "enchantment": enchantment,
            "market": market,
            "sell_city": sell_city,
            "sort_by": sort_by,
        },
    )


@router.get("/{item_id}", response_model=ItemDetailResponse)
def get_item(
    request: Request,
    item_id: str,
    city: str = Query("Lymhurst"),
    market: str = Query("marketplace"),
    sell_city: str | None = Query(None),
    exclude_cities: str | None = Query(None, description="Comma-separated cities to exclude"),
    use_focus: bool = Query(False, description="Whether to include focus cost in profit calculations"),
) -> ItemDetailResponse:
    state = _get_state(request)

    if market not in VALID_MARKETS:
        raise HTTPException(400, f"Invalid market: {market}")

    excluded = frozenset(c.strip() for c in exclude_cities.split(",") if c.strip()) if exclude_cities else frozenset()

    # Score all items for the requested city/market
    items = _scored_items(state, city, market, "return_rate_pct", sell_city=sell_city, exclude_cities=excluded, use_focus=use_focus)
    target = next((i for i in items if i.product_id == item_id), None)
    if target is None:
        raise HTTPException(404, f"Item not found: {item_id}")

    recipe = state.get_recipe(item_id)
    cost_breakdown: list[MaterialCost] = []
    optimized_material_cost: float | None = None
    optimized_profit: float | None = None
    if recipe:
        from ...scoring import _get_unit_prices, _index_prices, find_cheapest_city_per_material

        price_idx = _index_prices(state.prices)
        unit_prices = _get_unit_prices(recipe.materials, price_idx, target.craft_city)
        if unit_prices:
            for m in recipe.materials:
                up = unit_prices.get(m.item_id, 0.0)
                cost_breakdown.append(
                    MaterialCost(
                        item_id=m.item_id,
                        quantity=m.quantity,
                        unit_price=up,
                        total_price=up * m.quantity,
                        is_artifact_component=m.is_artifact_component,
                    )
                )

            # Find cheapest city for each material across all cities
            cheapest = find_cheapest_city_per_material(recipe.materials, price_idx)
            for mc in cost_breakdown:
                info = cheapest.get(mc.item_id)
                if info:
                    mc.best_buy_city = info[0]
                    mc.best_buy_price = info[1]

            # Calculate optimized material cost (using cheapest prices)
            optimized_material_cost = sum(
                cheapest[m.item_id][1] * m.quantity
                for m in recipe.materials
                if m.item_id in cheapest
            )

            # Calculate optimized profit using RRR ratio
            if target.material_cost and target.material_cost > 0:
                rrr_ratio = target.effective_craft_cost / target.material_cost
                optimized_effective_cost = optimized_material_cost * rrr_ratio
                optimized_profit = target.net_revenue - optimized_effective_cost

    # City comparison
    city_comparison: list[CityComparison] = []
    for comp_city in PRD_CITY_LOCATIONS:
        if comp_city in excluded:
            continue
        city_items = rank_items_v2(
            [recipe] if recipe else [],
            state.prices,
            state.city_bonuses,
            state.config,
            craft_city=comp_city,
            sell_mode=market,
            sell_city=sell_city,
            exclude_cities=excluded,
            use_focus=use_focus,
        )
        match = next((i for i in city_items if i.product_id == item_id), None)
        city_comparison.append(
            CityComparison(
                city=comp_city,
                return_rate_pct=match.return_rate_pct if match else None,
                profit_absolute=match.profit_absolute if match else None,
                sell_price=match.sell_price if match else None,
            )
        )

    # Fetch daily volume from history API
    daily_volume: float | None = None
    try:
        sell_location = "Black Market" if market == "black_market" else target.craft_city
        client = AlbionAPIClient()
        history = client.get_history_bulk([item_id], sell_location, quality=1, days=7)
        client.close()
        rows = history.get(item_id, [])
        # API v2 returns {data: [{item_count, avg_price, timestamp}, ...]} per row
        data_points: list[dict] = []
        for row in rows:
            data_points.extend(row.get("data", []))
        if data_points:
            daily_volume = _extract_daily_volume(data_points)
    except Exception:
        daily_volume = None

    return ItemDetailResponse(
        item=ScoredItemSchema(**_item_dict(target)),
        cost_breakdown=cost_breakdown,
        city_comparison=city_comparison,
        optimized_material_cost=optimized_material_cost,
        optimized_profit=optimized_profit,
        daily_volume=daily_volume,
    )


def _item_dict(item: ScoredItem) -> dict:
    return {
        "product_id": item.product_id,
        "craft_city": item.craft_city,
        "sell_mode": item.sell_mode,
        "material_cost": item.material_cost,
        "effective_craft_cost": item.effective_craft_cost,
        "setup_fee": item.setup_fee,
        "sales_tax": item.sales_tax,
        "sell_price": item.sell_price,
        "net_revenue": item.net_revenue,
        "profit_absolute": item.profit_absolute,
        "return_rate_pct": item.return_rate_pct,
        "focus_cost": item.focus_cost,
        "profit_per_focus": item.profit_per_focus,
        "freshness_score": item.freshness_score,
        "volume_score": item.volume_score,
        "volume_norm": item.volume_norm,
        "best_city": item.best_city,
        "final_score": item.final_score,
        "bm_sell_price": item.bm_sell_price,
        "bm_net_revenue": item.bm_net_revenue,
        "bm_profit": item.bm_profit,
        "bm_return_rate_pct": item.bm_return_rate_pct,
    }


def _matches_category(item: ScoredItem, category: str, state: AppState) -> bool:
    recipe = state.get_recipe(item.product_id)
    if recipe is None:
        return False
    return recipe.category == category


def _matches_tier(item: ScoredItem, tier: int, state: AppState) -> bool:
    recipe = state.get_recipe(item.product_id)
    return recipe is not None and recipe.tier == tier


def _matches_enchantment(item: ScoredItem, enchantment: int, state: AppState) -> bool:
    recipe = state.get_recipe(item.product_id)
    return recipe is not None and recipe.enchantment == enchantment

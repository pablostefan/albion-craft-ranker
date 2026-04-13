"""Pydantic v2 schemas for API request params and response bodies."""
from __future__ import annotations

from pydantic import BaseModel, Field


class ScoredItemSchema(BaseModel):
    product_id: str
    craft_city: str
    sell_mode: str
    material_cost: float
    effective_craft_cost: float
    setup_fee: float
    sales_tax: float
    sell_price: float
    net_revenue: float
    profit_absolute: float
    return_rate_pct: float
    focus_cost: int
    profit_per_focus: float
    freshness_score: float
    volume_score: float
    volume_norm: float
    best_city: str
    final_score: float
    bm_sell_price: float | None = None
    bm_net_revenue: float | None = None
    bm_profit: float | None = None
    bm_return_rate_pct: float | None = None
    daily_volume: float | None = None
    display_name: str = ""


class ItemsResponse(BaseModel):
    items: list[ScoredItemSchema]
    total: int
    filters_applied: dict[str, str | int | float | None]


class MaterialCost(BaseModel):
    item_id: str
    quantity: int
    unit_price: float
    total_price: float
    is_artifact_component: bool
    best_buy_city: str | None = None
    best_buy_price: float | None = None


class CityComparison(BaseModel):
    city: str
    return_rate_pct: float | None = None
    profit_absolute: float | None = None
    sell_price: float | None = None


class ItemDetailResponse(BaseModel):
    item: ScoredItemSchema
    cost_breakdown: list[MaterialCost]
    city_comparison: list[CityComparison]
    optimized_material_cost: float | None = None
    optimized_profit: float | None = None
    daily_volume: float | None = None


class CityBonusSchema(BaseModel):
    category: str
    bonus_pct: float


class CitySchema(BaseModel):
    name: str
    bonuses: list[CityBonusSchema]


class CitiesResponse(BaseModel):
    cities: list[CitySchema]


class ConfigResponse(BaseModel):
    setup_fee_rate: float
    premium_tax_rate: float
    normal_tax_rate: float
    is_premium: bool
    profit_weight: float
    focus_weight: float
    volume_weight: float
    freshness_weight: float
    min_profit: float
    sales_tax_rate: float

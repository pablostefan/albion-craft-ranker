"""Dependency injection for the FastAPI application."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..models import Recipe, ScoringConfig
from ..rrr_engine import DEFAULT_CITY_BONUSES
from .cache import TTLCache

if TYPE_CHECKING:
    from ..albion_client import MarketPrice


@dataclass
class AppState:
    """Singleton holding application state shared across requests."""

    recipes: list[Recipe] = field(default_factory=list)
    prices: list[MarketPrice] = field(default_factory=list)
    city_bonuses: dict[str, dict[str, float]] = field(default_factory=lambda: dict(DEFAULT_CITY_BONUSES))
    config: ScoringConfig = field(default_factory=ScoringConfig)
    cache: TTLCache = field(default_factory=lambda: TTLCache(ttl_seconds=300.0))

    # Recipe index for fast lookup by product_id
    _recipe_index: dict[str, Recipe] = field(default_factory=dict, repr=False)

    def build_recipe_index(self) -> None:
        self._recipe_index = {r.product_id: r for r in self.recipes}

    def get_recipe(self, product_id: str) -> Recipe | None:
        return self._recipe_index.get(product_id)

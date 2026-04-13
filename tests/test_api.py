"""Tests for FastAPI REST API layer (task_007)."""
from __future__ import annotations

import time
import unittest
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from src.albion_client import MarketPrice
from src.api.app import create_app
from src.api.cache import TTLCache
from src.api.dependencies import AppState
from src.models import Material, Recipe, ScoredItem, ScoringConfig

_NOW = datetime(2026, 4, 12, 12, 0, 0, tzinfo=timezone.utc)


# ─────────────────────────────────────────────────────────────────────────────
# Test helpers
# ─────────────────────────────────────────────────────────────────────────────

def _mp(
    item_id: str,
    city: str,
    sell_min: float = 0.0,
    buy_max: float = 0.0,
    staleness_h: float = 1.0,
) -> MarketPrice:
    past_dt = _NOW - timedelta(hours=staleness_h)
    date_str = past_dt.isoformat()
    return MarketPrice(
        item_id=item_id,
        city=city,
        quality=1,
        sell_price_min=sell_min,
        buy_price_max=buy_max,
        sell_price_min_date=date_str,
        buy_price_max_date=date_str,
        now_provider=lambda: _NOW,
    )


def _recipe(
    product_id: str = "T4_CLOTH_ARMOR",
    category: str = "cloth_armor",
    tier: int = 4,
    enchantment: int = 0,
    materials: list[Material] | None = None,
    focus_cost: int = 100,
    is_artifact: bool = False,
    amount_crafted: int = 1,
) -> Recipe:
    if materials is None:
        materials = [Material(item_id="T4_CLOTH", quantity=8)]
    return Recipe(
        product_id=product_id,
        category=category,
        tier=tier,
        enchantment=enchantment,
        materials=materials,
        focus_cost=focus_cost,
        is_artifact=is_artifact,
        amount_crafted=amount_crafted,
    )


def _build_state(
    recipes: list[Recipe] | None = None,
    prices: list[MarketPrice] | None = None,
    config: ScoringConfig | None = None,
) -> AppState:
    """Build an AppState with defaults for testing."""
    r = recipes or [
        _recipe("T4_CLOTH_ARMOR", "cloth_armor", tier=4, enchantment=0),
        _recipe(
            "T4_LEATHER_ARMOR",
            "leather_armor",
            tier=4,
            enchantment=0,
            materials=[Material(item_id="T4_LEATHER", quantity=8)],
        ),
        _recipe(
            "T5_CLOTH_ARMOR",
            "cloth_armor",
            tier=5,
            enchantment=1,
            materials=[Material(item_id="T5_CLOTH", quantity=16)],
        ),
    ]
    p = prices or [
        # T4_CLOTH_ARMOR materials + product
        _mp("T4_CLOTH", "Lymhurst", sell_min=100, buy_max=90),
        _mp("T4_CLOTH_ARMOR", "Lymhurst", sell_min=2000, buy_max=1800),
        # T4_LEATHER_ARMOR materials + product
        _mp("T4_LEATHER", "Lymhurst", sell_min=120, buy_max=100),
        _mp("T4_LEATHER_ARMOR", "Lymhurst", sell_min=2500, buy_max=2200),
        # T5_CLOTH_ARMOR materials + product
        _mp("T5_CLOTH", "Lymhurst", sell_min=300, buy_max=280),
        _mp("T5_CLOTH_ARMOR", "Lymhurst", sell_min=8000, buy_max=7500),
        # Black Market entries
        _mp("T4_CLOTH_ARMOR", "Black Market", sell_min=0, buy_max=1900),
        _mp("T4_LEATHER_ARMOR", "Black Market", sell_min=0, buy_max=2400),
    ]
    state = AppState(
        recipes=r,
        prices=p,
        config=config or ScoringConfig(),
    )
    state.build_recipe_index()
    return state


def _make_client(state: AppState | None = None) -> TestClient:
    s = state or _build_state()
    app = create_app(state=s)
    return TestClient(app, raise_server_exceptions=False)


# ─────────────────────────────────────────────────────────────────────────────
# GET /items
# ─────────────────────────────────────────────────────────────────────────────


class TestListItems(unittest.TestCase):
    def setUp(self) -> None:
        self.client = _make_client()

    def test_returns_json_with_items_and_total(self) -> None:
        resp = self.client.get("/items")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("items", body)
        self.assertIn("total", body)
        self.assertIsInstance(body["items"], list)
        self.assertGreater(body["total"], 0)

    def test_items_have_return_rate_pct(self) -> None:
        resp = self.client.get("/items")
        body = resp.json()
        for item in body["items"]:
            self.assertIn("return_rate_pct", item)

    def test_filter_by_city(self) -> None:
        resp = self.client.get("/items", params={"city": "Lymhurst"})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["filters_applied"]["city"], "Lymhurst")

    def test_filter_by_category(self) -> None:
        resp = self.client.get("/items", params={"category": "cloth_armor"})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        # All returned items should be cloth_armor
        for item in body["items"]:
            self.assertIn("CLOTH_ARMOR", item["product_id"])

    def test_filter_by_tier(self) -> None:
        resp = self.client.get("/items", params={"tier": 4})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        for item in body["items"]:
            self.assertIn("T4_", item["product_id"])

    def test_filter_by_enchantment(self) -> None:
        resp = self.client.get("/items", params={"enchantment": 1})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        # Only T5_CLOTH_ARMOR has enchantment=1 in fixtures
        self.assertGreater(len(body["items"]), 0)
        self.assertEqual(body["items"][0]["product_id"], "T5_CLOTH_ARMOR")

    def test_sort_by_profit(self) -> None:
        resp = self.client.get("/items", params={"sort_by": "profit"})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        profits = [i["profit_absolute"] for i in body["items"]]
        self.assertEqual(profits, sorted(profits, reverse=True))

    def test_sort_by_profit_per_focus(self) -> None:
        resp = self.client.get("/items", params={"sort_by": "profit_per_focus"})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        vals = [i["profit_per_focus"] for i in body["items"]]
        self.assertEqual(vals, sorted(vals, reverse=True))

    def test_pagination_limit_offset(self) -> None:
        resp_all = self.client.get("/items", params={"limit": 100})
        total = resp_all.json()["total"]

        resp_page = self.client.get("/items", params={"limit": 1, "offset": 0})
        body = resp_page.json()
        self.assertEqual(len(body["items"]), 1)
        self.assertEqual(body["total"], total)

        if total > 1:
            resp_page2 = self.client.get("/items", params={"limit": 1, "offset": 1})
            body2 = resp_page2.json()
            self.assertEqual(len(body2["items"]), 1)
            self.assertNotEqual(body["items"][0]["product_id"], body2["items"][0]["product_id"])

    def test_black_market_toggle(self) -> None:
        resp = self.client.get("/items", params={"market": "black_market"})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        for item in body["items"]:
            self.assertEqual(item["sell_mode"], "black_market")

    def test_invalid_market_returns_400(self) -> None:
        resp = self.client.get("/items", params={"market": "invalid"})
        self.assertEqual(resp.status_code, 400)

    def test_invalid_sort_by_returns_400(self) -> None:
        resp = self.client.get("/items", params={"sort_by": "invalid"})
        self.assertEqual(resp.status_code, 400)

    def test_filters_applied_in_response(self) -> None:
        resp = self.client.get("/items", params={"city": "Lymhurst", "category": "cloth_armor"})
        body = resp.json()
        fa = body["filters_applied"]
        self.assertEqual(fa["city"], "Lymhurst")
        self.assertEqual(fa["category"], "cloth_armor")

    def test_sell_city_query_param_accepted(self) -> None:
        resp = self.client.get("/items", params={"sell_city": "Caerleon"})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["filters_applied"]["sell_city"], "Caerleon")

    def test_sell_city_defaults_to_none(self) -> None:
        resp = self.client.get("/items")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIsNone(body["filters_applied"]["sell_city"])

    def test_order_asc_returns_ascending_sort(self) -> None:
        resp = self.client.get("/items", params={"sort_by": "profit", "order": "asc"})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        profits = [i["profit_absolute"] for i in body["items"]]
        self.assertEqual(profits, sorted(profits))

    def test_order_desc_returns_descending_sort(self) -> None:
        resp = self.client.get("/items", params={"sort_by": "profit", "order": "desc"})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        profits = [i["profit_absolute"] for i in body["items"]]
        self.assertEqual(profits, sorted(profits, reverse=True))

    def test_order_invalid_returns_422(self) -> None:
        resp = self.client.get("/items", params={"order": "invalid"})
        self.assertEqual(resp.status_code, 422)


# ─────────────────────────────────────────────────────────────────────────────
# GET /items/{item_id}
# ─────────────────────────────────────────────────────────────────────────────


class TestGetItem(unittest.TestCase):
    def setUp(self) -> None:
        self.client = _make_client()

    def test_get_item_returns_detail(self) -> None:
        resp = self.client.get("/items/T4_CLOTH_ARMOR")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("item", body)
        self.assertIn("cost_breakdown", body)
        self.assertIn("city_comparison", body)
        self.assertEqual(body["item"]["product_id"], "T4_CLOTH_ARMOR")

    def test_cost_breakdown_has_materials(self) -> None:
        resp = self.client.get("/items/T4_CLOTH_ARMOR")
        body = resp.json()
        breakdown = body["cost_breakdown"]
        self.assertGreater(len(breakdown), 0)
        first = breakdown[0]
        self.assertIn("item_id", first)
        self.assertIn("quantity", first)
        self.assertIn("unit_price", first)
        self.assertIn("total_price", first)

    def test_city_comparison_has_entries(self) -> None:
        resp = self.client.get("/items/T4_CLOTH_ARMOR")
        body = resp.json()
        comparison = body["city_comparison"]
        self.assertGreater(len(comparison), 0)
        city_names = [c["city"] for c in comparison]
        self.assertIn("Lymhurst", city_names)

    def test_item_not_found(self) -> None:
        resp = self.client.get("/items/NONEXISTENT_ITEM")
        self.assertEqual(resp.status_code, 404)

    def test_get_item_with_non_default_city_and_market(self) -> None:
        """GET /items/{id}?city=Martlock&market=black_market accepts non-default params."""
        state = _build_state(
            prices=[
                _mp("T4_CLOTH", "Lymhurst", sell_min=100, buy_max=90),
                _mp("T4_CLOTH_ARMOR", "Lymhurst", sell_min=2000, buy_max=1800),
                _mp("T4_CLOTH", "Martlock", sell_min=95, buy_max=85),
                _mp("T4_CLOTH_ARMOR", "Martlock", sell_min=1900, buy_max=1700),
                _mp("T4_CLOTH_ARMOR", "Black Market", sell_min=0, buy_max=1900),
                _mp("T4_LEATHER", "Lymhurst", sell_min=120, buy_max=100),
                _mp("T4_LEATHER_ARMOR", "Lymhurst", sell_min=2500, buy_max=2200),
                _mp("T5_CLOTH", "Lymhurst", sell_min=300, buy_max=280),
                _mp("T5_CLOTH_ARMOR", "Lymhurst", sell_min=8000, buy_max=7500),
            ],
        )
        client = _make_client(state)
        resp = client.get("/items/T4_CLOTH_ARMOR", params={"city": "Martlock", "market": "black_market"})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["item"]["product_id"], "T4_CLOTH_ARMOR")

    def test_get_item_invalid_market_returns_400(self) -> None:
        resp = self.client.get("/items/T4_CLOTH_ARMOR", params={"market": "invalid_value"})
        self.assertEqual(resp.status_code, 400)


# ─────────────────────────────────────────────────────────────────────────────
# GET /cities
# ─────────────────────────────────────────────────────────────────────────────


class TestListCities(unittest.TestCase):
    def setUp(self) -> None:
        self.client = _make_client()

    def test_returns_cities_with_bonuses(self) -> None:
        resp = self.client.get("/cities")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("cities", body)
        self.assertGreater(len(body["cities"]), 0)

    def test_city_has_bonuses_list(self) -> None:
        resp = self.client.get("/cities")
        body = resp.json()
        for city in body["cities"]:
            self.assertIn("name", city)
            self.assertIn("bonuses", city)
            self.assertIsInstance(city["bonuses"], list)
            if city["bonuses"]:
                b = city["bonuses"][0]
                self.assertIn("category", b)
                self.assertIn("bonus_pct", b)


# ─────────────────────────────────────────────────────────────────────────────
# GET /config
# ─────────────────────────────────────────────────────────────────────────────


class TestGetConfig(unittest.TestCase):
    def setUp(self) -> None:
        self.client = _make_client()

    def test_returns_scoring_config(self) -> None:
        resp = self.client.get("/config")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("setup_fee_rate", body)
        self.assertIn("is_premium", body)
        self.assertIn("sales_tax_rate", body)
        self.assertIn("profit_weight", body)


# ─────────────────────────────────────────────────────────────────────────────
# OpenAPI docs
# ─────────────────────────────────────────────────────────────────────────────


class TestOpenAPIDocs(unittest.TestCase):
    def setUp(self) -> None:
        self.client = _make_client()

    def test_docs_endpoint(self) -> None:
        resp = self.client.get("/docs")
        self.assertEqual(resp.status_code, 200)

    def test_openapi_json(self) -> None:
        resp = self.client.get("/openapi.json")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("paths", body)
        self.assertIn("/items", body["paths"])
        self.assertIn("/cities", body["paths"])
        self.assertIn("/config", body["paths"])


# ─────────────────────────────────────────────────────────────────────────────
# Cache
# ─────────────────────────────────────────────────────────────────────────────


class TestTTLCache(unittest.TestCase):
    def test_get_returns_none_for_missing_key(self) -> None:
        cache = TTLCache(ttl_seconds=300.0)
        self.assertIsNone(cache.get(("a", "b")))

    def test_set_and_get(self) -> None:
        cache = TTLCache(ttl_seconds=300.0)
        cache.set(("a", "b"), [1, 2, 3])
        self.assertEqual(cache.get(("a", "b")), [1, 2, 3])

    def test_ttl_expiry(self) -> None:
        cache = TTLCache(ttl_seconds=0.01)
        cache.set(("a",), "value")
        time.sleep(0.02)
        self.assertIsNone(cache.get(("a",)))

    def test_invalidate_all(self) -> None:
        cache = TTLCache()
        cache.set(("a",), 1)
        cache.set(("b",), 2)
        cache.invalidate_all()
        self.assertIsNone(cache.get(("a",)))
        self.assertIsNone(cache.get(("b",)))

    def test_cache_prevents_recomputation(self) -> None:
        """Two requests within TTL should return same cached result."""
        client = _make_client()
        resp1 = client.get("/items")
        resp2 = client.get("/items")
        self.assertEqual(resp1.json(), resp2.json())


# ─────────────────────────────────────────────────────────────────────────────
# CORS
# ─────────────────────────────────────────────────────────────────────────────


class TestCORS(unittest.TestCase):
    def test_cors_allows_localhost_3000(self) -> None:
        client = _make_client()
        resp = client.options(
            "/items",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        self.assertIn("access-control-allow-origin", resp.headers)
        self.assertEqual(resp.headers["access-control-allow-origin"], "http://localhost:3000")


if __name__ == "__main__":
    unittest.main()

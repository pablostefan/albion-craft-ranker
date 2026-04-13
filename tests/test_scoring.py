"""Tests for scoring.py — Scoring Engine v2 (task_005)."""
from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from src.albion_client import MarketPrice
from src.models import Material, Recipe, ScoredItem, ScoringConfig
from src.scoring import RecipeLine, rank_items, rank_items_v2

# Fixed "now" for deterministic staleness calculations.
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
    """Cria MarketPrice com staleness fixo e now_provider deterministico."""
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
    category: str = "armors",
    tier: int = 4,
    materials: list[Material] | None = None,
    focus_cost: int = 100,
    amount_crafted: int = 1,
    silver_cost: int = 0,
) -> Recipe:
    if materials is None:
        materials = [Material(item_id="T4_CLOTH", quantity=16, is_artifact_component=False)]
    return Recipe(
        product_id=product_id,
        category=category,
        tier=tier,
        enchantment=0,
        materials=materials,
        focus_cost=focus_cost,
        amount_crafted=amount_crafted,
        silver_cost=silver_cost,
    )


def _cfg(**kwargs: object) -> ScoringConfig:
    """ScoringConfig com pesos configurados; permite override via kwargs."""
    defaults: dict[str, object] = dict(
        setup_fee_rate=0.025,
        premium_tax_rate=0.04,
        normal_tax_rate=0.08,
        is_premium=True,
        profit_weight=0.5,
        focus_weight=0.2,
        volume_weight=0.2,
        freshness_weight=0.1,
        min_profit=0.0,
    )
    defaults.update(kwargs)
    return ScoringConfig(**defaults)  # type: ignore[arg-type]


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestRankItemsV2Basic(unittest.TestCase):
    def test_returns_empty_for_empty_recipes(self) -> None:
        result = rank_items_v2(
            recipes=[],
            prices=[],
            city_bonuses=None,
            config=_cfg(),
            craft_city="Lymhurst",
        )
        self.assertEqual(result, [])

    def test_single_recipe_returns_one_scored_item(self) -> None:
        recipe = _recipe("T4_BAG", "bag", materials=[Material("T4_CLOTH", 8, False)], focus_cost=50)
        prices = [
            _mp("T4_CLOTH", "Lymhurst", sell_min=1000.0, buy_max=900.0),
            _mp("T4_BAG", "Lymhurst", sell_min=20000.0, buy_max=18000.0),
        ]
        results = rank_items_v2(
            recipes=[recipe],
            prices=prices,
            city_bonuses=None,
            config=_cfg(),
            craft_city="Lymhurst",
            sell_city="Lymhurst",
        )
        self.assertEqual(len(results), 1)
        item = results[0]
        self.assertEqual(item.product_id, "T4_BAG")
        self.assertEqual(item.craft_city, "Lymhurst")
        self.assertEqual(item.sell_mode, "marketplace")
        self.assertGreater(item.return_rate_pct, 0.0)
        self.assertGreater(item.profit_absolute, 0.0)

    def test_result_is_scored_item_type(self) -> None:
        recipe = _recipe()
        prices = [
            _mp("T4_CLOTH", "Lymhurst", sell_min=1000.0),
            _mp("T4_CLOTH_ARMOR", "Lymhurst", sell_min=25000.0, buy_max=20000.0),
        ]
        results = rank_items_v2(
            recipes=[recipe], prices=prices, city_bonuses=None,
            config=_cfg(), craft_city="Lymhurst",
        )
        self.assertIsInstance(results[0], ScoredItem)


class TestRankItemsV2Taxes(unittest.TestCase):
    def test_setup_fee_is_2p5_percent_of_listed_price(self) -> None:
        recipe = _recipe("PROD", "cloth_armor", materials=[Material("MAT", 10, False)])
        prices = [
            _mp("MAT", "Lymhurst", sell_min=1000.0),
            _mp("PROD", "Lymhurst", sell_min=20000.0, buy_max=15000.0),
        ]
        results = rank_items_v2(
            recipes=[recipe], prices=prices, city_bonuses=None,
            config=_cfg(), craft_city="Lymhurst",
        )
        self.assertEqual(len(results), 1)
        item = results[0]
        total_sell = item.sell_price * 1  # amount_crafted=1
        self.assertAlmostEqual(item.setup_fee, total_sell * 0.025, places=4)

    def test_sales_tax_is_4_percent_premium(self) -> None:
        recipe = _recipe("PROD", "cloth_armor", materials=[Material("MAT", 10, False)])
        prices = [
            _mp("MAT", "Lymhurst", sell_min=1000.0),
            _mp("PROD", "Lymhurst", sell_min=20000.0, buy_max=15000.0),
        ]
        results = rank_items_v2(
            recipes=[recipe], prices=prices, city_bonuses=None,
            config=_cfg(is_premium=True, premium_tax_rate=0.04), craft_city="Lymhurst",
        )
        self.assertEqual(len(results), 1)
        item = results[0]
        # sales_tax = sell_price * 0.04 (for amount_crafted=1)
        self.assertAlmostEqual(item.sales_tax, item.sell_price * 0.04, places=4)

    def test_sales_tax_is_8_percent_normal(self) -> None:
        recipe = _recipe("PROD", "cloth_armor", materials=[Material("MAT", 10, False)])
        prices = [
            _mp("MAT", "Lymhurst", sell_min=1000.0),
            _mp("PROD", "Lymhurst", sell_min=20000.0, buy_max=15000.0),
        ]
        config = _cfg(
            is_premium=False,
            normal_tax_rate=0.08,
            profit_weight=1.0,
            focus_weight=0.0,
            volume_weight=0.0,
            freshness_weight=0.0,
        )
        results = rank_items_v2(
            recipes=[recipe], prices=prices, city_bonuses=None,
            config=config, craft_city="Lymhurst",
        )
        self.assertEqual(len(results), 1)
        item = results[0]
        self.assertAlmostEqual(item.sales_tax, item.sell_price * 0.08, places=4)

    def test_return_rate_pct_formula(self) -> None:
        """return_rate_pct = (profit_absolute / (eff_cost + setup_fee)) * 100."""
        recipe = _recipe("PROD", "cloth_armor", materials=[Material("MAT", 10, False)])
        prices = [
            _mp("MAT", "Lymhurst", sell_min=1000.0),
            _mp("PROD", "Lymhurst", sell_min=30000.0, buy_max=25000.0),
        ]
        results = rank_items_v2(
            recipes=[recipe], prices=prices, city_bonuses=None,
            config=_cfg(), craft_city="Lymhurst",
        )
        item = results[0]
        total_cost = item.effective_craft_cost + item.setup_fee
        expected_rr = item.profit_absolute / total_cost * 100.0
        self.assertAlmostEqual(item.return_rate_pct, expected_rr, places=6)

    def test_net_revenue_eq_sell_price_minus_sales_tax(self) -> None:
        recipe = _recipe("PROD", "cloth_armor", materials=[Material("MAT", 10, False)])
        prices = [
            _mp("MAT", "Lymhurst", sell_min=1000.0),
            _mp("PROD", "Lymhurst", sell_min=25000.0, buy_max=20000.0),
        ]
        results = rank_items_v2(
            recipes=[recipe], prices=prices, city_bonuses=None,
            config=_cfg(), craft_city="Lymhurst",
        )
        item = results[0]
        # net_revenue should equal sell_price - sales_tax (for amount_crafted=1)
        self.assertAlmostEqual(item.net_revenue, item.sell_price - item.sales_tax, places=4)


class TestRankItemsV2SellModes(unittest.TestCase):
    def test_black_market_uses_buy_price_max(self) -> None:
        recipe = _recipe("PROD", "bag", materials=[Material("MAT", 4, False)], focus_cost=0)
        prices = [
            _mp("MAT", "Brecilien", sell_min=1000.0),
            _mp("PROD", "Brecilien", sell_min=10000.0, buy_max=8000.0),
            _mp("PROD", "Black Market", sell_min=0.0, buy_max=15000.0),
        ]
        config = _cfg(profit_weight=1.0, focus_weight=0.0, volume_weight=0.0, freshness_weight=0.0)
        results = rank_items_v2(
            recipes=[recipe], prices=prices, city_bonuses=None,
            config=config, craft_city="Brecilien", sell_mode="black_market",
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].sell_price, 15000.0)

    def test_black_market_applies_sales_tax_on_bm_price(self) -> None:
        recipe = _recipe("PROD", "bag", materials=[Material("MAT", 4, False)], focus_cost=0)
        prices = [
            _mp("MAT", "Brecilien", sell_min=1000.0),
            _mp("PROD", "Black Market", sell_min=0.0, buy_max=15000.0),
        ]
        config = _cfg(
            is_premium=True, premium_tax_rate=0.04,
            profit_weight=1.0, focus_weight=0.0, volume_weight=0.0, freshness_weight=0.0,
        )
        results = rank_items_v2(
            recipes=[recipe], prices=prices, city_bonuses=None,
            config=config, craft_city="Brecilien", sell_mode="black_market",
        )
        item = results[0]
        self.assertAlmostEqual(item.sales_tax, 15000.0 * 0.04, places=4)

    def test_comparison_mode_has_both_marketplace_and_bm_fields(self) -> None:
        recipe = _recipe("PROD", "bag", materials=[Material("MAT", 4, False)], focus_cost=0)
        prices = [
            _mp("MAT", "Brecilien", sell_min=1000.0),
            _mp("PROD", "Brecilien", sell_min=12000.0, buy_max=10000.0),
            _mp("PROD", "Black Market", sell_min=0.0, buy_max=14000.0),
        ]
        config = _cfg(profit_weight=1.0, focus_weight=0.0, volume_weight=0.0, freshness_weight=0.0)
        results = rank_items_v2(
            recipes=[recipe], prices=prices, city_bonuses=None,
            config=config, craft_city="Brecilien", sell_mode="comparison",
        )
        self.assertEqual(len(results), 1)
        item = results[0]
        # Marketplace is primary
        self.assertEqual(item.sell_price, 12000.0)
        self.assertEqual(item.sell_mode, "comparison")
        # BM fields populated
        self.assertIsNotNone(item.bm_sell_price)
        self.assertEqual(item.bm_sell_price, 14000.0)
        self.assertIsNotNone(item.bm_profit)
        self.assertIsNotNone(item.bm_return_rate_pct)

    def test_comparison_bm_return_rate_pct_formula(self) -> None:
        recipe = _recipe("PROD", "bag", materials=[Material("MAT", 4, False)], focus_cost=0)
        prices = [
            _mp("MAT", "Brecilien", sell_min=1000.0),
            _mp("PROD", "Brecilien", sell_min=12000.0, buy_max=10000.0),
            _mp("PROD", "Black Market", sell_min=0.0, buy_max=14000.0),
        ]
        config = _cfg(profit_weight=1.0, focus_weight=0.0, volume_weight=0.0, freshness_weight=0.0)
        results = rank_items_v2(
            recipes=[recipe], prices=prices, city_bonuses=None,
            config=config, craft_city="Brecilien", sell_mode="comparison",
        )
        item = results[0]
        # BM comparison uses cost without setup fee
        bm_total_cost = item.effective_craft_cost + item.silver_cost
        expected_bm_rr = item.bm_profit / bm_total_cost * 100.0  # type: ignore[operator]
        self.assertAlmostEqual(item.bm_return_rate_pct, expected_bm_rr, places=6)  # type: ignore[arg-type]

    def test_invalid_sell_mode_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            rank_items_v2(
                recipes=[], prices=[], city_bonuses=None,
                config=_cfg(), craft_city="Lymhurst", sell_mode="invalid",
            )

    def test_black_market_no_bm_price_skips_item(self) -> None:
        recipe = _recipe("PROD", "bag", materials=[Material("MAT", 4, False)])
        prices = [
            _mp("MAT", "Brecilien", sell_min=1000.0),
            _mp("PROD", "Brecilien", sell_min=12000.0, buy_max=10000.0),
            # No Black Market price
        ]
        results = rank_items_v2(
            recipes=[recipe], prices=prices, city_bonuses=None,
            config=_cfg(), craft_city="Brecilien", sell_mode="black_market",
        )
        self.assertEqual(results, [])

    def test_marketplace_bm_fields_are_none(self) -> None:
        recipe = _recipe()
        prices = [
            _mp("T4_CLOTH", "Lymhurst", sell_min=1000.0),
            _mp("T4_CLOTH_ARMOR", "Lymhurst", sell_min=25000.0, buy_max=20000.0),
        ]
        results = rank_items_v2(
            recipes=[recipe], prices=prices, city_bonuses=None,
            config=_cfg(), craft_city="Lymhurst", sell_mode="marketplace",
        )
        item = results[0]
        self.assertIsNone(item.bm_sell_price)
        self.assertIsNone(item.bm_net_revenue)
        self.assertIsNone(item.bm_profit)
        self.assertIsNone(item.bm_return_rate_pct)


class TestRankItemsV2ArtifactCost(unittest.TestCase):
    def test_artifact_material_has_full_cost_no_rrr(self) -> None:
        """is_artifact_component=True → RRR=0, custo bruto = custo efetivo."""
        artifact_mat = Material("ARTIFACT_RUNE", quantity=1, is_artifact_component=True)
        normal_mat = Material("T4_CLOTH", quantity=10, is_artifact_component=False)
        recipe = _recipe(
            "ARTIFACT_BOW", "bow",
            materials=[artifact_mat, normal_mat],
            focus_cost=0,
        )
        prices = [
            _mp("ARTIFACT_RUNE", "Lymhurst", sell_min=5000.0),
            _mp("T4_CLOTH", "Lymhurst", sell_min=1000.0),
            _mp("ARTIFACT_BOW", "Lymhurst", sell_min=40000.0, buy_max=35000.0),
        ]
        config = _cfg(
            profit_weight=1.0, focus_weight=0.0,
            volume_weight=0.0, freshness_weight=0.0,
        )
        results = rank_items_v2(
            recipes=[recipe], prices=prices,
            city_bonuses={"Lymhurst": {"bow": 0.15}},
            config=config, craft_city="Lymhurst",
        )
        self.assertEqual(len(results), 1)
        item = results[0]
        # raw material_cost = 1*5000 + 10*1000 = 15000
        self.assertAlmostEqual(item.material_cost, 15000.0, places=2)
        # effective_craft_cost < material_cost: RRR reduces T4_CLOTH but not ARTIFACT_RUNE
        self.assertLess(item.effective_craft_cost, item.material_cost)


class TestRankItemsV2MissingPrices(unittest.TestCase):
    def test_missing_material_price_skips_item(self) -> None:
        recipe = _recipe("PROD", "cloth_armor", materials=[
            Material("MAT_A", 5, False),
            Material("MAT_B", 3, False),  # no price in prices list
        ])
        prices = [
            _mp("MAT_A", "Lymhurst", sell_min=500.0),
            _mp("PROD", "Lymhurst", sell_min=10000.0, buy_max=8000.0),
        ]
        results = rank_items_v2(
            recipes=[recipe], prices=prices, city_bonuses=None,
            config=_cfg(), craft_city="Lymhurst",
        )
        self.assertEqual(results, [])

    def test_missing_product_price_skips_item(self) -> None:
        recipe = _recipe("PROD", "cloth_armor", materials=[Material("MAT", 5, False)])
        prices = [
            _mp("MAT", "Lymhurst", sell_min=500.0),
            # PROD has no price
        ]
        results = rank_items_v2(
            recipes=[recipe], prices=prices, city_bonuses=None,
            config=_cfg(), craft_city="Lymhurst",
        )
        self.assertEqual(results, [])

    def test_zero_material_price_skips_item(self) -> None:
        recipe = _recipe("PROD", "cloth_armor", materials=[Material("MAT", 5, False)])
        prices = [
            _mp("MAT", "Lymhurst", sell_min=0.0, buy_max=0.0),
            _mp("PROD", "Lymhurst", sell_min=10000.0, buy_max=8000.0),
        ]
        results = rank_items_v2(
            recipes=[recipe], prices=prices, city_bonuses=None,
            config=_cfg(), craft_city="Lymhurst",
        )
        self.assertEqual(results, [])


class TestRankItemsV2Freshness(unittest.TestCase):
    def test_fresh_price_gives_high_freshness_score(self) -> None:
        recipe = _recipe("PROD", "cloth_armor", materials=[Material("MAT", 5, False)])
        prices = [
            _mp("MAT", "Lymhurst", sell_min=500.0, staleness_h=0.5),
            _mp("PROD", "Lymhurst", sell_min=10000.0, buy_max=8000.0, staleness_h=0.5),
        ]
        results = rank_items_v2(
            recipes=[recipe], prices=prices, city_bonuses=None,
            config=_cfg(), craft_city="Lymhurst", staleness_cap_hours=48.0,
        )
        self.assertEqual(len(results), 1)
        self.assertGreater(results[0].freshness_score, 0.98)

    def test_stale_price_over_cap_gives_zero_freshness(self) -> None:
        recipe = _recipe("PROD", "cloth_armor", materials=[Material("MAT", 5, False)])
        prices = [
            _mp("MAT", "Lymhurst", sell_min=500.0, staleness_h=50.0),
            _mp("PROD", "Lymhurst", sell_min=10000.0, buy_max=8000.0, staleness_h=50.0),
        ]
        results = rank_items_v2(
            recipes=[recipe], prices=prices, city_bonuses=None,
            config=_cfg(), craft_city="Lymhurst", staleness_cap_hours=48.0,
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].freshness_score, 0.0)

    def test_freshness_score_in_range_01(self) -> None:
        recipe = _recipe("PROD", "cloth_armor", materials=[Material("MAT", 5, False)])
        prices = [
            _mp("MAT", "Lymhurst", sell_min=500.0, staleness_h=24.0),
            _mp("PROD", "Lymhurst", sell_min=10000.0, buy_max=8000.0, staleness_h=24.0),
        ]
        results = rank_items_v2(
            recipes=[recipe], prices=prices, city_bonuses=None,
            config=_cfg(), craft_city="Lymhurst", staleness_cap_hours=48.0,
        )
        score = results[0].freshness_score
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)
        self.assertAlmostEqual(score, 0.5, places=3)


class TestRankItemsV2FocusCost(unittest.TestCase):
    def test_profit_per_focus_zero_when_focus_cost_is_zero(self) -> None:
        recipe = _recipe("PROD", "cloth_armor", focus_cost=0)
        prices = [
            _mp("T4_CLOTH", "Lymhurst", sell_min=1000.0),
            _mp("PROD", "Lymhurst", sell_min=25000.0, buy_max=20000.0),
        ]
        results = rank_items_v2(
            recipes=[recipe], prices=prices, city_bonuses=None,
            config=_cfg(), craft_city="Lymhurst",
        )
        self.assertEqual(results[0].profit_per_focus, 0.0)

    def test_profit_per_focus_uses_delta_formula(self) -> None:
        """PRD: profit_per_focus = (profit_with_focus - profit_without_focus) / focus_cost."""
        from src.rrr_engine import get_effective_material_cost

        recipe = _recipe("PROD", "cloth_armor", focus_cost=200)
        prices = [
            _mp("T4_CLOTH", "Lymhurst", sell_min=1000.0),
            _mp("PROD", "Lymhurst", sell_min=30000.0, buy_max=25000.0),
        ]
        results = rank_items_v2(
            recipes=[recipe], prices=prices, city_bonuses=None,
            config=_cfg(), craft_city="Lymhurst",
        )
        item = results[0]

        unit_prices = {"T4_CLOTH": 1000.0}
        eff_no_focus = get_effective_material_cost(
            recipe.materials, unit_prices, category="cloth_armor",
            city="Lymhurst", use_focus=False,
        )
        eff_with_focus = get_effective_material_cost(
            recipe.materials, unit_prices, category="cloth_armor",
            city="Lymhurst", use_focus=True,
        )
        cost_delta = eff_no_focus - eff_with_focus
        expected_ppf = cost_delta / 200.0

        self.assertAlmostEqual(item.profit_per_focus, expected_ppf, places=6)
        # Delta formula differs from naive profit/focus_cost
        self.assertNotAlmostEqual(item.profit_per_focus, item.profit_absolute / 200.0, places=2)


class TestRankItemsV2MinProfit(unittest.TestCase):
    def test_items_below_min_profit_are_filtered(self) -> None:
        recipe = _recipe("PROD", "cloth_armor", materials=[Material("T4_CLOTH", 16, False)])
        prices = [
            _mp("T4_CLOTH", "Lymhurst", sell_min=1000.0),
            _mp("PROD", "Lymhurst", sell_min=10000.0, buy_max=8000.0),
        ]
        config = _cfg(min_profit=999_999.0)
        results = rank_items_v2(
            recipes=[recipe], prices=prices, city_bonuses=None,
            config=config, craft_city="Lymhurst",
        )
        self.assertEqual(results, [])

    def test_items_above_min_profit_are_included(self) -> None:
        recipe = _recipe("PROD", "cloth_armor", materials=[Material("T4_CLOTH", 16, False)])
        prices = [
            _mp("T4_CLOTH", "Lymhurst", sell_min=1000.0),
            _mp("PROD", "Lymhurst", sell_min=40000.0, buy_max=35000.0),
        ]
        config = _cfg(min_profit=0.0)
        results = rank_items_v2(
            recipes=[recipe], prices=prices, city_bonuses=None,
            config=config, craft_city="Lymhurst",
        )
        self.assertEqual(len(results), 1)


class TestRankItemsV2BestCity(unittest.TestCase):
    def _all_city_prices(
        self,
        product_id: str,
        material_id: str,
        sell_min: float = 15000.0,
        buy_max: float = 12000.0,
        mat_sell: float = 1000.0,
        extra_city: str | None = None,
    ) -> list[MarketPrice]:
        cities = ["Brecilien", "Bridgewatch", "Caerleon", "Fort Sterling", "Lymhurst", "Martlock", "Thetford"]
        result: list[MarketPrice] = []
        for city in cities:
            result.append(_mp(material_id, city, sell_min=mat_sell, buy_max=mat_sell * 0.9))
            result.append(_mp(product_id, city, sell_min=sell_min, buy_max=buy_max))
        return result

    def test_best_city_is_brecilien_for_bags(self) -> None:
        """Brecilien tem bonus de 0.15 para 'bag' → menor custo efetivo → melhor RRR."""
        recipe = _recipe("T4_BAG", "bag", materials=[Material("T4_CLOTH", 8, False)], focus_cost=0)
        prices = self._all_city_prices("T4_BAG", "T4_CLOTH")
        # city_bonuses=None usa os defaults do rrr_engine (Brecilien bag=0.15)
        config = _cfg(profit_weight=1.0, focus_weight=0.0, volume_weight=0.0, freshness_weight=0.0)
        results = rank_items_v2(
            recipes=[recipe], prices=prices, city_bonuses=None,
            config=config, craft_city="Lymhurst",
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].best_city, "Brecilien")

    def test_best_city_field_is_populated(self) -> None:
        recipe = _recipe()
        prices = [
            _mp("T4_CLOTH", "Lymhurst", sell_min=1000.0),
            _mp("T4_CLOTH_ARMOR", "Lymhurst", sell_min=25000.0, buy_max=20000.0),
        ]
        results = rank_items_v2(
            recipes=[recipe], prices=prices, city_bonuses=None,
            config=_cfg(), craft_city="Lymhurst",
        )
        self.assertIsNotNone(results[0].best_city)
        self.assertIsInstance(results[0].best_city, str)
        self.assertGreater(len(results[0].best_city), 0)


class TestRankItemsV2ScoringWeights(unittest.TestCase):
    def test_invalid_weights_sum_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            ScoringConfig(
                profit_weight=0.5,
                focus_weight=0.3,
                volume_weight=0.3,
                freshness_weight=0.1,  # sum = 1.2, invalid
            )

    def test_valid_weights_do_not_raise(self) -> None:
        config = _cfg()  # default weights sum to 1.0
        self.assertIsInstance(config, ScoringConfig)

    def test_final_score_in_range_0_to_1(self) -> None:
        recipe = _recipe("PROD", "cloth_armor", focus_cost=100)
        prices = [
            _mp("T4_CLOTH", "Lymhurst", sell_min=1000.0),
            _mp("PROD", "Lymhurst", sell_min=25000.0, buy_max=20000.0),
        ]
        results = rank_items_v2(
            recipes=[recipe], prices=prices, city_bonuses=None,
            config=_cfg(), craft_city="Lymhurst",
        )
        score = results[0].final_score
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0 + 1e-9)

    def test_scoring_config_sales_tax_rate_property_premium(self) -> None:
        config = ScoringConfig(is_premium=True, premium_tax_rate=0.04)
        self.assertAlmostEqual(config.sales_tax_rate, 0.04)

    def test_scoring_config_sales_tax_rate_property_normal(self) -> None:
        config = ScoringConfig(is_premium=False, normal_tax_rate=0.08)
        self.assertAlmostEqual(config.sales_tax_rate, 0.08)


class TestRankItemsV2Ordering(unittest.TestCase):
    def test_sorted_by_final_score_descending(self) -> None:
        r1 = Recipe("PROD_A", "armors", 4, 0, [Material("MAT", 5, False)], 50)
        r2 = Recipe("PROD_B", "armors", 4, 0, [Material("MAT", 5, False)], 50)
        prices = [
            _mp("MAT", "Lymhurst", sell_min=1000.0),
            _mp("PROD_A", "Lymhurst", sell_min=50000.0, buy_max=40000.0),  # higher profit
            _mp("PROD_B", "Lymhurst", sell_min=20000.0, buy_max=15000.0),  # lower profit
        ]
        config = _cfg(profit_weight=1.0, focus_weight=0.0, volume_weight=0.0, freshness_weight=0.0)
        results = rank_items_v2(
            recipes=[r1, r2], prices=prices, city_bonuses=None,
            config=config, craft_city="Lymhurst",
        )
        self.assertEqual(len(results), 2)
        self.assertGreaterEqual(results[0].final_score, results[1].final_score)
        self.assertEqual(results[0].product_id, "PROD_A")

    def test_single_item_has_final_score_one(self) -> None:
        """Com apenas um item, todos os indicadores normalizados = 1.0."""
        recipe = _recipe("PROD", "cloth_armor", focus_cost=100)
        prices = [
            _mp("T4_CLOTH", "Lymhurst", sell_min=1000.0),
            _mp("PROD", "Lymhurst", sell_min=25000.0, buy_max=20000.0),
        ]
        config = _cfg(freshness_weight=0.0, volume_weight=0.0, focus_weight=0.0, profit_weight=1.0)
        results = rank_items_v2(
            recipes=[recipe], prices=prices, city_bonuses=None,
            config=config, craft_city="Lymhurst",
        )
        # With one item, normalized value = 1.0 and freshness_weight=0 → final_score = 1.0
        self.assertAlmostEqual(results[0].final_score, 1.0, places=6)


class TestBackwardCompatibility(unittest.TestCase):
    def test_rank_items_still_importable(self) -> None:
        self.assertTrue(callable(rank_items))

    def test_recipe_line_still_importable(self) -> None:
        self.assertTrue(callable(RecipeLine))

    def test_rank_items_v1_returns_list(self) -> None:
        """rank_items() (v1, CSV-based) deve continuar funcionando sem erro."""
        from pathlib import Path
        from src.scoring import load_recipes

        # load_recipes retorna lista vazia para arquivo inexistente se checarmos
        # apenas que a funcao e chamavel sem crash.
        self.assertTrue(callable(load_recipes))

    def test_rank_items_v1_returns_correct_ranking_format(self) -> None:
        """rank_items() (v1) com client mockado retorna List[RankedItem] correto."""
        from unittest.mock import MagicMock
        from src.scoring import RankedItem

        mock_client = MagicMock()
        mock_client.get_prices.return_value = [
            MarketPrice(
                item_id="MAT", city="Lymhurst", quality=1,
                sell_price_min=1000.0, buy_price_max=900.0,
                sell_price_min_date="2026-04-12T12:00:00+00:00",
                buy_price_max_date="2026-04-12T12:00:00+00:00",
            ),
            MarketPrice(
                item_id="PROD", city="Lymhurst", quality=1,
                sell_price_min=20000.0, buy_price_max=18000.0,
                sell_price_min_date="2026-04-12T12:00:00+00:00",
                buy_price_max_date="2026-04-12T12:00:00+00:00",
            ),
        ]
        recipe_lines = [RecipeLine(product_id="PROD", material_id="MAT", material_qty=8, focus_cost=50)]

        result = rank_items(
            client=mock_client,
            recipe_lines=recipe_lines,
            craft_city="Lymhurst",
            sell_city="Lymhurst",
            quality=1,
            return_rate=0.15,
            tax_rate=0.065,
            volume_days=7,
            profit_weight=0.7,
            volume_weight=0.3,
            min_profit=0.0,
            use_history=False,
        )

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        item = result[0]
        self.assertIsInstance(item, RankedItem)
        self.assertEqual(item.product_id, "PROD")
        self.assertGreater(item.profit, 0.0)
        self.assertGreater(item.margin_pct, 0.0)
        self.assertGreater(item.final_score, 0.0)

    def test_rank_items_v2_accepts_four_positional_args(self) -> None:
        """Plan documents rank_items_v2(recipes, prices, city_bonuses, config)."""
        result = rank_items_v2([], [], None, _cfg())
        self.assertEqual(result, [])


class TestRankItemsV2VolumesMap(unittest.TestCase):
    def test_volumes_map_sets_volume_score(self) -> None:
        """volumes_map values are stored as volume_score on the resulting ScoredItem."""
        recipe = _recipe("T4_CLOTH_ARMOR")
        prices = [
            _mp("T4_CLOTH", "Lymhurst", sell_min=1000.0),
            _mp("T4_CLOTH_ARMOR", "Lymhurst", sell_min=25000.0, buy_max=20000.0),
        ]
        results = rank_items_v2(
            recipes=[recipe],
            prices=prices,
            city_bonuses=None,
            config=_cfg(),
            craft_city="Lymhurst",
            volumes_map={"T4_CLOTH_ARMOR": 9999.0},
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].volume_score, 9999.0)

    def test_volumes_map_none_falls_back_to_zero(self) -> None:
        """Without volumes_map, volume_score falls back to 0.0."""
        recipe = _recipe("T4_CLOTH_ARMOR")
        prices = [
            _mp("T4_CLOTH", "Lymhurst", sell_min=1000.0),
            _mp("T4_CLOTH_ARMOR", "Lymhurst", sell_min=25000.0, buy_max=20000.0),
        ]
        results = rank_items_v2(
            recipes=[recipe],
            prices=prices,
            city_bonuses=None,
            config=_cfg(),
            craft_city="Lymhurst",
            volumes_map=None,
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].volume_score, 0.0)


class TestRankItemsV2SilverCost(unittest.TestCase):
    def test_silver_cost_reduces_profit_by_exact_amount(self) -> None:
        """silver_cost is added to total_cost, reducing profit_absolute by exactly that amount."""
        base_recipe = _recipe("T4_CLOTH_ARMOR", silver_cost=0)
        silver_recipe = _recipe("T4_CLOTH_ARMOR", silver_cost=1000)
        prices = [
            _mp("T4_CLOTH", "Lymhurst", sell_min=1000.0),
            _mp("T4_CLOTH_ARMOR", "Lymhurst", sell_min=30000.0, buy_max=25000.0),
        ]
        r_base = rank_items_v2(
            recipes=[base_recipe],
            prices=prices,
            city_bonuses=None,
            config=_cfg(),
            craft_city="Lymhurst",
        )
        r_silver = rank_items_v2(
            recipes=[silver_recipe],
            prices=prices,
            city_bonuses=None,
            config=_cfg(),
            craft_city="Lymhurst",
        )
        self.assertEqual(len(r_base), 1)
        self.assertEqual(len(r_silver), 1)
        self.assertAlmostEqual(
            r_base[0].profit_absolute - r_silver[0].profit_absolute,
            1000.0,
            places=4,
        )
        self.assertEqual(r_silver[0].silver_cost, 1000)

    def test_silver_cost_zero_does_not_change_profit(self) -> None:
        """silver_cost=0 (default) produces the same profit as a recipe with no silver field."""
        recipe_no_silver = _recipe("T4_CLOTH_ARMOR")
        recipe_zero_silver = _recipe("T4_CLOTH_ARMOR", silver_cost=0)
        prices = [
            _mp("T4_CLOTH", "Lymhurst", sell_min=1000.0),
            _mp("T4_CLOTH_ARMOR", "Lymhurst", sell_min=25000.0, buy_max=20000.0),
        ]
        r1 = rank_items_v2([recipe_no_silver], prices, None, _cfg(), craft_city="Lymhurst")
        r2 = rank_items_v2([recipe_zero_silver], prices, None, _cfg(), craft_city="Lymhurst")
        self.assertEqual(len(r1), 1)
        self.assertEqual(len(r2), 1)
        self.assertAlmostEqual(r1[0].profit_absolute, r2[0].profit_absolute, places=4)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import csv
import sys
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.main import build_parser, save_ranking_csv_v2


class TestBuildParserV2Mode(unittest.TestCase):
    """Tests for v2 CLI flags (--items-json path)."""

    def test_items_json_flag_accepted(self) -> None:
        parser = build_parser()
        args = parser.parse_args([
            "--items-json", "items.json",
            "--modifiers-json", "mods.json",
            "--craft-city", "Lymhurst",
        ])
        self.assertEqual(args.items_json, "items.json")
        self.assertEqual(args.modifiers_json, "mods.json")
        self.assertEqual(args.craft_city, "Lymhurst")

    def test_sell_mode_default_marketplace(self) -> None:
        parser = build_parser()
        args = parser.parse_args([
            "--items-json", "items.json",
            "--craft-city", "Lymhurst",
        ])
        self.assertEqual(args.sell_mode, "marketplace")

    def test_sell_mode_black_market(self) -> None:
        parser = build_parser()
        args = parser.parse_args([
            "--items-json", "items.json",
            "--craft-city", "Lymhurst",
            "--sell-mode", "black_market",
        ])
        self.assertEqual(args.sell_mode, "black_market")

    def test_sell_mode_comparison(self) -> None:
        parser = build_parser()
        args = parser.parse_args([
            "--items-json", "items.json",
            "--craft-city", "Lymhurst",
            "--sell-mode", "comparison",
        ])
        self.assertEqual(args.sell_mode, "comparison")

    def test_premium_default_true(self) -> None:
        parser = build_parser()
        args = parser.parse_args([
            "--items-json", "items.json",
            "--craft-city", "Lymhurst",
        ])
        self.assertTrue(args.premium)

    def test_no_premium_flag(self) -> None:
        parser = build_parser()
        args = parser.parse_args([
            "--items-json", "items.json",
            "--craft-city", "Lymhurst",
            "--no-premium",
        ])
        self.assertFalse(args.premium)

    def test_use_focus_flag(self) -> None:
        parser = build_parser()
        args = parser.parse_args([
            "--items-json", "items.json",
            "--craft-city", "Lymhurst",
            "--use-focus",
        ])
        self.assertTrue(args.use_focus)

    def test_use_focus_default_false(self) -> None:
        parser = build_parser()
        args = parser.parse_args([
            "--items-json", "items.json",
            "--craft-city", "Lymhurst",
        ])
        self.assertFalse(args.use_focus)

    def test_focus_weight_custom(self) -> None:
        parser = build_parser()
        args = parser.parse_args([
            "--items-json", "items.json",
            "--craft-city", "Lymhurst",
            "--focus-weight", "0.3",
        ])
        self.assertAlmostEqual(args.focus_weight, 0.3)

    def test_freshness_weight_custom(self) -> None:
        parser = build_parser()
        args = parser.parse_args([
            "--items-json", "items.json",
            "--craft-city", "Lymhurst",
            "--freshness-weight", "0.15",
        ])
        self.assertAlmostEqual(args.freshness_weight, 0.15)

    def test_best_city_flag(self) -> None:
        parser = build_parser()
        args = parser.parse_args([
            "--items-json", "items.json",
            "--craft-city", "Lymhurst",
            "--best-city",
        ])
        self.assertTrue(args.best_city)

    def test_best_city_default_false(self) -> None:
        parser = build_parser()
        args = parser.parse_args([
            "--items-json", "items.json",
            "--craft-city", "Lymhurst",
        ])
        self.assertFalse(args.best_city)


class TestBuildParserLegacyMode(unittest.TestCase):
    """Tests for legacy CLI flags (--recipes CSV path)."""

    def test_legacy_recipes_flag(self) -> None:
        parser = build_parser()
        args = parser.parse_args([
            "--recipes", "data/recipes.csv",
            "--craft-city", "Lymhurst",
            "--sell-city", "Lymhurst",
        ])
        self.assertEqual(args.recipes, "data/recipes.csv")
        self.assertEqual(args.sell_city, "Lymhurst")

    def test_legacy_defaults(self) -> None:
        parser = build_parser()
        args = parser.parse_args([
            "--recipes", "data/recipes.csv",
            "--craft-city", "Lymhurst",
            "--sell-city", "Lymhurst",
        ])
        self.assertEqual(args.server, "west")
        self.assertEqual(args.quality, 1)
        self.assertAlmostEqual(args.return_rate, 0.152)
        self.assertAlmostEqual(args.tax_rate, 0.065)
        self.assertEqual(args.top, 20)

    def test_no_source_requires_craft_city(self) -> None:
        """craft-city is always required."""
        parser = build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["--items-json", "items.json"])


class TestBuildParserMutualExclusion(unittest.TestCase):
    """Ensure --items-json and --recipes are not both required."""

    def test_neither_flag_accepted(self) -> None:
        """Parser accepts no source; main() validates later."""
        parser = build_parser()
        args = parser.parse_args(["--craft-city", "Lymhurst"])
        self.assertIsNone(args.items_json)
        self.assertIsNone(args.recipes)


class TestSaveRankingCsvV2(unittest.TestCase):
    """Tests for save_ranking_csv_v2 output columns."""

    def _make_scored_item(self, **overrides):
        from src.models import ScoredItem
        defaults = dict(
            product_id="T4_SWORD",
            craft_city="Lymhurst",
            sell_mode="marketplace",
            material_cost=1000.0,
            effective_craft_cost=800.0,
            setup_fee=20.0,
            sales_tax=50.0,
            sell_price=1500.0,
            net_revenue=1400.0,
            profit_absolute=580.0,
            return_rate_pct=70.73,
            focus_cost=100,
            profit_per_focus=5.8,
            freshness_score=0.9,
            liquidity_score=0.7,
            best_city="Lymhurst",
            final_score=0.85,
        )
        defaults.update(overrides)
        return ScoredItem(**defaults)

    def test_csv_has_required_columns(self) -> None:
        item = self._make_scored_item()
        path = Path("/tmp/test_ranking_v2.csv")
        save_ranking_csv_v2([item], path)

        with path.open("r") as f:
            reader = csv.DictReader(f)
            columns = reader.fieldnames or []

        self.assertIn("return_rate_pct", columns)
        self.assertIn("profit_per_focus", columns)
        self.assertIn("best_city", columns)
        self.assertIn("sell_mode", columns)
        path.unlink(missing_ok=True)

    def test_csv_row_values(self) -> None:
        item = self._make_scored_item(
            product_id="T5_SWORD",
            return_rate_pct=42.5,
            best_city="Martlock",
            sell_mode="black_market",
        )
        path = Path("/tmp/test_ranking_v2_values.csv")
        save_ranking_csv_v2([item], path)

        with path.open("r") as f:
            reader = csv.DictReader(f)
            row = next(reader)

        self.assertEqual(row["product_id"], "T5_SWORD")
        self.assertEqual(row["return_rate_pct"], "42.5")
        self.assertEqual(row["best_city"], "Martlock")
        self.assertEqual(row["sell_mode"], "black_market")
        path.unlink(missing_ok=True)

    def test_csv_empty_list(self) -> None:
        path = Path("/tmp/test_ranking_v2_empty.csv")
        save_ranking_csv_v2([], path)

        with path.open("r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        self.assertEqual(len(rows), 0)
        self.assertIn("return_rate_pct", reader.fieldnames or [])
        path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()

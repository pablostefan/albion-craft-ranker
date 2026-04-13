from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from src.recipe_parser import parse_items_json


class ParseItemsJsonTests(unittest.TestCase):
    def _write_items_json(self, payload: dict) -> Path:
        tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        with tmp:
            json.dump(payload, tmp)
        return Path(tmp.name)

    def test_parse_items_json_normalizes_dict_craftresource_and_enchantment_override(self) -> None:
        payload = {
            "items": {
                "equipmentitem": [
                    {
                        "@uniquename": "T4_HEAD_CLOTH_SET1",
                        "@tier": "4",
                        "@craftingcategory": "cloth_helmet",
                        "craftingrequirements": {
                            "@craftingfocus": "429",
                            "craftresource": {
                                "@uniquename": "T4_CLOTH",
                                "@count": "8",
                            },
                        },
                        "enchantments": {
                            "enchantment": {
                                "@enchantmentlevel": "1",
                                "craftingrequirements": {
                                    "@craftingfocus": "750",
                                    "craftresource": {
                                        "@uniquename": "T4_CLOTH_LEVEL1",
                                        "@count": "8",
                                        "@enchantmentlevel": "1",
                                    },
                                },
                            }
                        },
                    }
                ]
            }
        }

        path = self._write_items_json(payload)

        recipes = parse_items_json(path)
        by_id = {recipe.product_id: recipe for recipe in recipes}

        base_recipe = by_id["T4_HEAD_CLOTH_SET1"]
        self.assertEqual(base_recipe.tier, 4)
        self.assertEqual(base_recipe.category, "cloth_helmet")
        self.assertEqual(base_recipe.enchantment, 0)
        self.assertEqual(base_recipe.focus_cost, 429)
        self.assertEqual(len(base_recipe.materials), 1)
        self.assertEqual(base_recipe.materials[0].item_id, "T4_CLOTH")
        self.assertEqual(base_recipe.materials[0].quantity, 8)

        enchanted_recipe = by_id["T4_HEAD_CLOTH_SET1@1"]
        self.assertEqual(enchanted_recipe.enchantment, 1)
        self.assertEqual(enchanted_recipe.focus_cost, 750)
        self.assertEqual(len(enchanted_recipe.materials), 1)
        self.assertEqual(enchanted_recipe.materials[0].item_id, "T4_CLOTH_LEVEL1")
        self.assertEqual(enchanted_recipe.materials[0].quantity, 8)

    def test_parse_items_json_uses_first_craftingrequirements_recipe_and_flags_artifacts(self) -> None:
        payload = {
            "items": {
                "weapon": [
                    {
                        "@uniquename": "T4_2H_BOW_KEEPER",
                        "@tier": "4",
                        "@craftingcategory": "bow",
                        "craftingrequirements": [
                            {
                                "@craftingfocus": "1715",
                                "craftresource": [
                                    {
                                        "@uniquename": "T4_PLANKS",
                                        "@count": "32",
                                    },
                                    {
                                        "@uniquename": "T4_ARTEFACT_2H_BOW_KEEPER",
                                        "@count": "1",
                                        "@maxreturnamount": "0",
                                    },
                                ],
                            },
                            {
                                "@craftingfocus": "1715",
                                "craftresource": [
                                    {
                                        "@uniquename": "T4_PLANKS",
                                        "@count": "32",
                                    },
                                    {
                                        "@uniquename": "T4_ARTEFACT_TOKEN_FAVOR_3",
                                        "@count": "1",
                                        "@maxreturnamount": "0",
                                    },
                                ],
                            },
                        ],
                    }
                ]
            }
        }

        path = self._write_items_json(payload)

        recipes = parse_items_json(path)

        self.assertEqual(len(recipes), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.product_id, "T4_2H_BOW_KEEPER")
        self.assertEqual(recipe.focus_cost, 1715)
        self.assertTrue(recipe.is_artifact)
        self.assertEqual(len(recipe.materials), 2)
        self.assertEqual(recipe.materials[0].item_id, "T4_PLANKS")
        self.assertFalse(recipe.materials[0].is_artifact_component)
        self.assertEqual(recipe.materials[1].item_id, "T4_ARTEFACT_2H_BOW_KEEPER")
        self.assertTrue(recipe.materials[1].is_artifact_component)

    def test_parse_items_json_filters_swaptransaction_and_noncraftable_items(self) -> None:
        payload = {
            "items": {
                "journalitem": [
                    {
                        "@uniquename": "T4_JOURNAL_LUMBERJACK_EMPTY",
                        "@tier": "4",
                        "@craftingcategory": "journal",
                        "craftingrequirements": {
                            "@swaptransaction": "true",
                        },
                    }
                ],
                "equipmentitem": [
                    {
                        "@uniquename": "T4_CAPE",
                        "@tier": "4",
                        "@craftingcategory": "cape",
                    },
                    {
                        "@uniquename": "T4_BAG",
                        "@tier": "4",
                        "@craftingcategory": "bag",
                        "craftingrequirements": {
                            "@amountoftoken": "58",
                            "craftresource": [
                                {
                                    "@uniquename": "T4_CLOTH",
                                    "@count": "8",
                                },
                                {
                                    "@uniquename": "T4_LEATHER",
                                    "@count": "8",
                                },
                            ],
                        },
                    },
                ]
            }
        }

        path = self._write_items_json(payload)

        recipes = parse_items_json(path)
        product_ids = {recipe.product_id for recipe in recipes}

        self.assertEqual(product_ids, {"T4_BAG"})
        recipe = recipes[0]
        self.assertEqual(recipe.focus_cost, 58)
        self.assertEqual(len(recipe.materials), 2)

    def test_parse_items_json_extracts_amount_crafted_for_batch_recipes(self) -> None:
        payload = {
            "items": {
                "consumableitem": [
                    {
                        "@uniquename": "T2_POTION_HEAL",
                        "@tier": "2",
                        "@craftingcategory": "potion",
                        "craftingrequirements": {
                            "@craftingfocus": "56",
                            "@amountcrafted": "5",
                            "craftresource": {
                                "@uniquename": "T2_AGARIC",
                                "@count": "8",
                            },
                        },
                    }
                ]
            }
        }

        path = self._write_items_json(payload)

        recipes = parse_items_json(path)

        self.assertEqual(len(recipes), 1)
        self.assertEqual(recipes[0].product_id, "T2_POTION_HEAL")
        self.assertEqual(recipes[0].amount_crafted, 5)


@unittest.skipUnless(
    os.environ.get("ITEMS_JSON_PATH") and Path(os.environ.get("ITEMS_JSON_PATH", "")).exists(),
    "Skipped: set ITEMS_JSON_PATH to the local ao-bin-dumps items.json to validate recipe coverage.",
)
class RecipeCoverageIntegrationTests(unittest.TestCase):
    """PRD acceptance criterion: >=3500 craftable recipes parsed from ao-bin-dumps items.json.

    Run with:
        ITEMS_JSON_PATH=/path/to/ao-bin-dumps/items.json python -m unittest discover -s tests
    """

    PRD_MIN_RECIPE_COUNT = 3500

    def test_item_count_meets_prd_minimum(self) -> None:
        items_json_path = Path(os.environ["ITEMS_JSON_PATH"])
        recipes = parse_items_json(items_json_path)
        self.assertGreaterEqual(
            len(recipes),
            self.PRD_MIN_RECIPE_COUNT,
            f"Expected at least {self.PRD_MIN_RECIPE_COUNT} craftable recipes from items.json, "
            f"got {len(recipes)}. Check recipe_parser for regressions.",
        )


if __name__ == "__main__":
    unittest.main()
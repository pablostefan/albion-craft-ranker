from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.models import Material
from src.rrr_engine import calculate_rrr, get_effective_material_cost, load_city_bonuses


class RRREngineTests(unittest.TestCase):
    def _write_crafting_modifiers(self, payload: dict) -> Path:
        tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        with tmp:
            json.dump(payload, tmp)
        return Path(tmp.name)

    def test_load_city_bonuses_filters_supported_city_model_and_ignores_halls(self) -> None:
        payload = {
            "craftingmodifiers": {
                "craftinglocation": [
                    {
                        "@clusterid": "1000",
                        "craftingbonus": {"@value": "0.18"},
                        "refiningbonus": {"@value": "0.18"},
                        "craftingmodifier": [
                            {"@name": "fiber", "@value": "0.40"},
                            {"@name": "bow", "@value": "0.15"},
                        ],
                    },
                    {
                        "@clusterid": "5000",
                        "craftingbonus": {"@value": "0.18"},
                        "refiningbonus": {"@value": "0.18"},
                        "craftingmodifier": [
                            {"@name": "bag", "@value": "0.15"},
                            {"@name": "potion", "@value": "0.15"},
                        ],
                    },
                    {
                        "@clusterid": "4300",
                        "craftingbonus": {"@value": "0.18"},
                        "refiningbonus": {"@value": "0.15"},
                        "craftingmodifier": [
                            {"@name": "axe", "@value": "0.15"},
                        ],
                    },
                ]
            }
        }

        path = self._write_crafting_modifiers(payload)

        bonuses = load_city_bonuses(path)

        self.assertEqual(set(bonuses), {"Brecilien", "Lymhurst"})
        self.assertAlmostEqual(bonuses["Lymhurst"]["fiber"], 0.40)
        self.assertAlmostEqual(bonuses["Lymhurst"]["bow"], 0.15)
        self.assertAlmostEqual(bonuses["Brecilien"]["bag"], 0.15)
        self.assertNotIn("Warrior Hall", bonuses)

    def test_calculate_rrr_matches_known_research_values(self) -> None:
        self.assertAlmostEqual(calculate_rrr("bow", "Lymhurst", False), 0.2481203008, places=6)
        self.assertAlmostEqual(calculate_rrr("bow", "Bridgewatch", False), 0.1525423729, places=6)
        self.assertAlmostEqual(calculate_rrr("bow", "Lymhurst", True), 0.4791666667, places=6)
        self.assertAlmostEqual(calculate_rrr("fiber", "Lymhurst", False), 0.3670886076, places=6)

    def test_calculate_rrr_accepts_specialization_bonus_in_percent_points(self) -> None:
        without_spec = calculate_rrr("bag", "Brecilien", True, spec_bonus=0)
        with_spec = calculate_rrr("bag", "Brecilien", True, spec_bonus=10)

        self.assertAlmostEqual(without_spec, 0.4791666667, places=6)
        self.assertAlmostEqual(with_spec, 0.5049504950, places=6)

    def test_artifact_materials_are_excluded_from_rrr_in_cost_calculation(self) -> None:
        materials = [
            Material(item_id="T4_PLANKS", quantity=32),
            Material(item_id="T4_ARTEFACT_2H_BOW_KEEPER", quantity=1, is_artifact_component=True),
        ]
        unit_prices = {
            "T4_PLANKS": 100.0,
            "T4_ARTEFACT_2H_BOW_KEEPER": 1_000.0,
        }

        effective_cost = get_effective_material_cost(
            materials,
            unit_prices,
            category="bow",
            city="Lymhurst",
            use_focus=False,
        )

        expected_rrr = calculate_rrr("bow", "Lymhurst", False)
        expected_cost = (32 * 100.0 * (1.0 - expected_rrr)) + 1_000.0

        self.assertAlmostEqual(effective_cost, expected_cost, places=6)


if __name__ == "__main__":
    unittest.main()
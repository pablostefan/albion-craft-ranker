from __future__ import annotations

import json
import warnings
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from .models import CityBonus, Material

# Task_002 follows the PRD city model: 7 cities only.
# The dump also contains Conquerors' Halls (4300, 1012, 0008) and Outlands entries,
# but those are intentionally excluded here so task_005 can reason about a stable city set.
SUPPORTED_CITY_BY_CLUSTER_ID: dict[str, str] = {
    "0000": "Thetford",
    "1000": "Lymhurst",
    "2000": "Bridgewatch",
    "3004": "Martlock",
    "4000": "Fort Sterling",
    "3003": "Caerleon",
    "5000": "Brecilien",
}

SUPPORTED_CITIES: tuple[str, ...] = tuple(sorted(SUPPORTED_CITY_BY_CLUSTER_ID.values()))
BASE_PRODUCTION_BONUS = 0.18
FOCUS_PRODUCTION_BONUS = 0.59

_DEFAULT_CITY_BONUS_SOURCE: dict[str, dict[str, float]] = {
    "Thetford": {
        "ore": 0.40,
        "meat_pig": 0.10,
        "mace": 0.15,
        "naturestaff": 0.15,
        "firestaff": 0.15,
        "leather_armor": 0.15,
        "cloth_helmet": 0.15,
    },
    "Lymhurst": {
        "fiber": 0.40,
        "meat_goose": 0.10,
        "sword": 0.15,
        "bow": 0.15,
        "arcanestaff": 0.15,
        "leather_helmet": 0.15,
        "leather_shoes": 0.15,
    },
    "Bridgewatch": {
        "rock": 0.40,
        "meat_goat": 0.10,
        "crossbow": 0.15,
        "dagger": 0.15,
        "cursestaff": 0.15,
        "plate_armor": 0.15,
        "cloth_shoes": 0.15,
    },
    "Martlock": {
        "hide": 0.40,
        "meat_cow": 0.10,
        "axe": 0.15,
        "quarterstaff": 0.15,
        "froststaff": 0.15,
        "plate_shoes": 0.15,
        "offhand": 0.15,
    },
    "Fort Sterling": {
        "wood": 0.40,
        "meat_chicken": 0.10,
        "meat_sheep": 0.10,
        "hammer": 0.15,
        "spear": 0.15,
        "holystaff": 0.15,
        "plate_helmet": 0.15,
        "cloth_armor": 0.15,
    },
    "Caerleon": {
        "gatherergear": 0.15,
        "tools": 0.15,
        "food": 0.15,
        "knuckles": 0.15,
        "shapeshifterstaff": 0.15,
    },
    "Brecilien": {
        "cape": 0.15,
        "bag": 0.15,
        "potion": 0.15,
    },
}

DEFAULT_CITY_BONUS_MODELS: tuple[CityBonus, ...] = tuple(
    CityBonus(city=city, category=category, bonus_rate=bonus_rate)
    for city, categories in _DEFAULT_CITY_BONUS_SOURCE.items()
    for category, bonus_rate in categories.items()
)

DEFAULT_CITY_BONUSES: dict[str, dict[str, float]] = {
    city: {category: bonus_rate for category, bonus_rate in categories.items()}
    for city, categories in _DEFAULT_CITY_BONUS_SOURCE.items()
}

_CATEGORY_ALIASES = {
    "war_gloves": "knuckles",
    "wargloves": "knuckles",
    "stone": "rock",
}


def load_city_bonuses(path: Path | str) -> dict[str, dict[str, float]]:
    with Path(path).open("r", encoding="utf-8") as handle:
        raw_data = json.load(handle)

    return parse_city_bonuses(raw_data)


def parse_city_bonuses(payload: Mapping[str, Any]) -> dict[str, dict[str, float]]:
    crafting_modifiers = payload.get("craftingmodifiers", payload)
    locations = _as_list(crafting_modifiers.get("craftinglocation"))

    bonuses: dict[str, dict[str, float]] = {}
    for location in locations:
        if not isinstance(location, Mapping):
            continue

        city = SUPPORTED_CITY_BY_CLUSTER_ID.get(str(location.get("@clusterid", "")))
        if city is None:
            continue

        modifiers: dict[str, float] = {}
        for modifier in _as_list(location.get("craftingmodifier")):
            if not isinstance(modifier, Mapping):
                continue
            category = _normalize_category(modifier.get("@name"))
            if not category:
                continue
            modifiers[category] = _as_float(modifier.get("@value"))

        bonuses[city] = modifiers

    return bonuses


def calculate_rrr(
    category: str,
    city: str,
    use_focus: bool,
    spec_bonus: float = 0.0,
    *,
    city_bonuses: Mapping[str, Mapping[str, float]] | None = None,
    is_artifact_component: bool = False,
) -> float:
    if is_artifact_component:
        return 0.0

    normalized_city = _normalize_city(city)
    normalized_category = _normalize_category(category)
    bonus_index = _resolve_city_bonuses(city_bonuses)

    if normalized_city not in bonus_index:
        raise ValueError(f"Cidade nao suportada para o modelo do task_002: {city}")

    production_bonus = BASE_PRODUCTION_BONUS
    production_bonus += bonus_index[normalized_city].get(normalized_category, 0.0)
    if use_focus:
        production_bonus += FOCUS_PRODUCTION_BONUS
    production_bonus += _normalize_bonus_input(spec_bonus)

    return 1.0 - (1.0 / (1.0 + production_bonus))


def get_material_rrr(
    material: Material,
    *,
    category: str,
    city: str,
    use_focus: bool,
    spec_bonus: float = 0.0,
    city_bonuses: Mapping[str, Mapping[str, float]] | None = None,
) -> float:
    return calculate_rrr(
        category,
        city,
        use_focus,
        spec_bonus=spec_bonus,
        city_bonuses=city_bonuses,
        is_artifact_component=material.is_artifact_component,
    )


def get_effective_material_cost(
    materials: Iterable[Material],
    unit_prices: Mapping[str, float],
    *,
    category: str,
    city: str,
    use_focus: bool,
    spec_bonus: float = 0.0,
    city_bonuses: Mapping[str, Mapping[str, float]] | None = None,
) -> float:
    total_cost = 0.0
    for material in materials:
        if material.item_id not in unit_prices:
            raise KeyError(f"Preco ausente para material: {material.item_id}")

        unit_price = float(unit_prices[material.item_id])
        material_rrr = get_material_rrr(
            material,
            category=category,
            city=city,
            use_focus=use_focus,
            spec_bonus=spec_bonus,
            city_bonuses=city_bonuses,
        )
        total_cost += material.quantity * unit_price * (1.0 - material_rrr)

    return total_cost


def _resolve_city_bonuses(
    city_bonuses: Mapping[str, Mapping[str, float]] | None,
) -> dict[str, dict[str, float]]:
    merged = {
        city: dict(categories)
        for city, categories in DEFAULT_CITY_BONUSES.items()
    }
    if city_bonuses is None:
        return merged

    parsed_cities = {_normalize_city(city): categories for city, categories in city_bonuses.items()}
    missing_cities = sorted(set(SUPPORTED_CITIES) - set(parsed_cities))
    if missing_cities:
        warnings.warn(
            "craftingmodifiers.json nao cobre todo o modelo de cidades do PRD; usando fallback documentado para: "
            + ", ".join(missing_cities),
            RuntimeWarning,
            stacklevel=3,
        )

    for city, categories in parsed_cities.items():
        if city not in merged:
            continue
        merged[city] = {
            _normalize_category(category): float(bonus_rate)
            for category, bonus_rate in categories.items()
        }

    return merged


def _normalize_city(city: str) -> str:
    normalized = " ".join(str(city).strip().split())
    for supported_city in SUPPORTED_CITIES:
        if supported_city.casefold() == normalized.casefold():
            return supported_city
    return normalized


def _normalize_category(category: Any) -> str:
    normalized = str(category or "").strip().lower().replace("-", "_").replace(" ", "_")
    return _CATEGORY_ALIASES.get(normalized, normalized)


def _normalize_bonus_input(bonus: float) -> float:
    numeric_bonus = float(bonus)
    if numeric_bonus > 1.0:
        return numeric_bonus / 100.0
    return numeric_bonus


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
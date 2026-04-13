from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import Material, Recipe


def parse_items_json(path: Path | str) -> list[Recipe]:
    with Path(path).open("r", encoding="utf-8") as handle:
        raw_data = json.load(handle)

    items_root = raw_data.get("items", raw_data)
    recipes: list[Recipe] = []

    for item in _iter_item_definitions(items_root):
        base_recipe = _parse_recipe_definition(item=item, enchantment=0, requirements=item.get("craftingrequirements"))
        if base_recipe is not None:
            recipes.append(base_recipe)

        enchantment_entries = _as_list(item.get("enchantments", {}).get("enchantment"))
        for enchantment_entry in enchantment_entries:
            if not isinstance(enchantment_entry, dict):
                continue
            enchantment_level = _as_int(enchantment_entry.get("@enchantmentlevel"))
            if enchantment_level <= 0:
                continue

            recipe = _parse_recipe_definition(
                item=item,
                enchantment=enchantment_level,
                requirements=enchantment_entry.get("craftingrequirements"),
            )
            if recipe is not None:
                recipes.append(recipe)

    recipes.sort(key=lambda recipe: recipe.product_id)
    return recipes


def _iter_item_definitions(items_root: Any) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    if not isinstance(items_root, dict):
        return entries

    for value in items_root.values():
        if isinstance(value, list):
            entries.extend(item for item in value if _is_item_definition(item))
            continue

        if isinstance(value, dict):
            if _is_item_definition(value):
                entries.append(value)
                continue

            for nested_value in value.values():
                if isinstance(nested_value, list):
                    entries.extend(item for item in nested_value if _is_item_definition(item))

    return entries


def _is_item_definition(candidate: Any) -> bool:
    return isinstance(candidate, dict) and "@uniquename" in candidate and (
        "craftingrequirements" in candidate or "enchantments" in candidate
    )


def _parse_recipe_definition(
    *,
    item: dict[str, Any],
    enchantment: int,
    requirements: Any,
) -> Recipe | None:
    recipe_data = _select_primary_recipe(requirements)
    if recipe_data is None or _is_swap_transaction(recipe_data):
        return None

    materials = _parse_materials(recipe_data)
    if not materials:
        return None

    product_id = str(item.get("@uniquename", "")).strip()
    if not product_id:
        return None
    if enchantment > 0:
        product_id = f"{product_id}@{enchantment}"

    return Recipe(
        product_id=product_id,
        category=str(item.get("@craftingcategory") or "").strip(),
        tier=_as_int(item.get("@tier")),
        enchantment=enchantment,
        materials=materials,
        focus_cost=_extract_focus_cost(recipe_data),
        is_artifact=any(material.is_artifact_component for material in materials),
        amount_crafted=max(1, _as_int(recipe_data.get("@amountcrafted"), default=1)),
    )


def _select_primary_recipe(requirements: Any) -> dict[str, Any] | None:
    normalized = _as_list(requirements)
    if not normalized:
        return None

    first = normalized[0]
    if not isinstance(first, dict):
        return None
    return first


def _parse_materials(recipe_data: dict[str, Any]) -> list[Material]:
    materials: list[Material] = []
    for resource in _as_list(recipe_data.get("craftresource")):
        if not isinstance(resource, dict):
            continue

        item_id = str(resource.get("@uniquename", "")).strip()
        if not item_id:
            continue

        materials.append(
            Material(
                item_id=item_id,
                quantity=_as_int(resource.get("@count")),
                is_artifact_component=str(resource.get("@maxreturnamount", "")).strip() == "0",
            )
        )

    return materials


def _extract_focus_cost(recipe_data: dict[str, Any]) -> int:
    crafting_focus = _as_int(recipe_data.get("@craftingfocus"), default=-1)
    if crafting_focus >= 0:
        return crafting_focus
    return _as_int(recipe_data.get("@amountoftoken"))


def _is_swap_transaction(recipe_data: dict[str, Any]) -> bool:
    return str(recipe_data.get("@swaptransaction", "")).strip().lower() == "true"


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default
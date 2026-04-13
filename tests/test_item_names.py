"""Tests for item_names.py — format_item_id utility."""
from __future__ import annotations

import pytest

from src.item_names import format_item_id


def test_format_item_id_basic() -> None:
    """Known Albion item IDs should produce readable names."""
    result = format_item_id("T4_ARMOR_LEATHER_SET1")
    assert "Leather" in result or "Armor" in result


def test_format_item_id_enchanted() -> None:
    """Enchantment suffix @N should be stripped."""
    result = format_item_id("T5_HEAD_PLATE_MAGE@2")
    assert "@" not in result
    assert result  # non-empty


def test_format_item_id_unknown_token() -> None:
    """Unknown tokens should not raise — fall back to title case."""
    result = format_item_id("T4_ZZZUNKNOWNZZZ_ITEM")
    assert isinstance(result, str)
    assert result  # non-empty


def test_format_item_id_empty() -> None:
    """Empty string input should not raise."""
    result = format_item_id("")
    assert isinstance(result, str)


def test_format_item_id_returns_string() -> None:
    """Return type must always be str."""
    for item_id in ["T8_2H_CROSSBOW", "T6_SHOES_CLOTH_SET3@1", "T4_OFF_TORCH"]:
        assert isinstance(format_item_id(item_id), str)


def test_format_item_id_cloth_armor() -> None:
    """Cloth adjective should appear before noun."""
    result = format_item_id("T4_CLOTH_ARMOR")
    assert "Cloth" in result
    assert "Armor" in result
    assert result.index("Cloth") < result.index("Armor")


def test_format_item_id_tier_in_output() -> None:
    """Tier suffix should appear in the output."""
    result = format_item_id("T6_SWORD")
    assert "T6" in result
    assert "Sword" in result


def test_format_item_id_enchant_suffix() -> None:
    """Enchantment level should appear as +N in the output."""
    result = format_item_id("T4_SWORD@1")
    assert "+1" in result
    assert "@" not in result

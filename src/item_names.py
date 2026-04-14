"""Utility for converting Albion Online item IDs to human-readable names."""

import re

_KNOWN_TOKENS: dict[str, str | None] = {
    "SWORD": "Sword",
    "BOW": "Bow",
    "CROSSBOW": "Crossbow",
    "STAFF": "Staff",
    "WAND": "Wand",
    "DAGGER": "Dagger",
    "HAMMER": "Hammer",
    "AXE": "Axe",
    "MACE": "Mace",
    "SPEAR": "Spear",
    "ARCANE": "Arcane",
    "CURSED": "Cursed",
    "HOLY": "Holy",
    "NATURE": "Nature",
    "FIRE": "Fire",
    "FROST": "Frost",
    "ARMOR": "Armor",
    "LEATHER": "Leather",
    "PLATE": "Plate",
    "CLOTH": "Cloth",
    "ROYAL": "Royal",
    "HEAD": "Head",
    "HELMET": "Helmet",
    "SHOES": "Shoes",
    "BOOTS": "Boots",
    "CAPE": "Cape",
    "BAG": "Bag",
    "OFF": "Off-Hand",
    "SHIELD": "Shield",
    "TORCH": "Torch",
    "ORB": "Orb",
    "BOOK": "Book",
    "TOTEM": "Totem",
    "HORN": "Horn",
    "FOCUS": "Focus",
    "LUTE": "Lute",
    "MORGANA": "Morgana",
    "KEEPER": "Keeper",
    "HERETIC": "Heretic",
    "UNDEAD": "Undead",
    "HELL": "Hell",
    "DEMON": "Demon",
    "KNUCKLES": "Knuckles",
    "GREAT": "Great",
    "BROADSWORD": "Broadsword",
    "HOARFROST": "Hoarfrost",
    "ENIGMATIC": "Enigmatic",
    "HALLOWEEN": "Halloween",
    "MARKET": "Market",
    "FACTION": "Faction",
    "SATCHEL": "Satchel",
    "INFO": "Info",
    "SET": None,  # bare SET token is dropped; SET{N} is handled separately
}

# Tokens that act as adjective/material modifiers and sort before noun tokens.
# This corrects cases like ARMOR_LEATHER -> "Leather Armor" rather than "Armor Leather".
_ADJECTIVE_TOKENS: frozenset[str] = frozenset({
    "LEATHER", "CLOTH", "PLATE", "ROYAL", "GREAT",
    "MORGANA", "KEEPER", "HERETIC", "UNDEAD", "HELL", "DEMON",
    "HALLOWEEN", "HOARFROST", "ENIGMATIC", "MARKET", "FACTION",
    "HOLY", "NATURE", "FIRE", "FROST", "ARCANE", "CURSED",
})

_FULL_ITEM_NAMES: dict[str, str] = {
    "QUESTITEM_TOKEN_AVALON": "Avalonian Energy",
    "QUESTITEM_TOKEN_MISTS": "Mists Energy",
    "QUESTITEM_TOKEN_ROYAL_T4": "Royal Sigil (T4)",
    "QUESTITEM_TOKEN_ROYAL_T5": "Royal Sigil (T5)",
    "QUESTITEM_TOKEN_ROYAL_T6": "Royal Sigil (T6)",
    "QUESTITEM_TOKEN_ROYAL_T7": "Royal Sigil (T7)",
    "QUESTITEM_TOKEN_ROYAL_T8": "Royal Sigil (T8)",
    "QUESTITEM_TOKEN_ARENA_CRYSTAL": "Arena Sigil (Crystal)",
    "QUESTITEM_TOKEN_ARENA_UNRANKED": "Arena Sigil",
    "QUESTITEM_TOKEN_SMUGGLER": "Smuggler Token",
}

_SET_RE = re.compile(r"^SET(\d+)$")
_TIER_RE = re.compile(r"^T(\d+)_")
_ENCHANT_RE = re.compile(r"@(\d+)$")


def format_item_id(item_id: str) -> str:
    """Convert an Albion Online item ID to a human-readable name.

    Examples:
        >>> format_item_id("T4_SWORD@1")
        'Sword T4 +1'
        >>> format_item_id("T6_ARMOR_LEATHER_SET3")
        'Leather Armor T6 .3'
    """
    if not item_id:
        return item_id

    override = _FULL_ITEM_NAMES.get(item_id)
    if override:
        return override

    try:
        remaining = item_id

        # Step 1: Extract enchantment suffix (@N)
        enchant: str | None = None
        enchant_match = _ENCHANT_RE.search(remaining)
        if enchant_match:
            enchant = enchant_match.group(1)
            remaining = remaining[: enchant_match.start()]

        # Step 2: Extract tier prefix (T\d+_)
        tier: str | None = None
        tier_match = _TIER_RE.match(remaining)
        if tier_match:
            tier = tier_match.group(1)
            remaining = remaining[tier_match.end():]

        # Step 3: Split by '_' and expand tokens
        raw_tokens = remaining.split("_") if remaining else []
        token_pairs: list[tuple[str, str]] = []
        variant: str | None = None

        for token in raw_tokens:
            if not token:
                continue
            # SET{N} variant suffix
            set_match = _SET_RE.match(token)
            if set_match:
                variant = set_match.group(1)
                continue
            # Known token expansion
            if token in _KNOWN_TOKENS:
                value = _KNOWN_TOKENS[token]
                if value is not None:
                    token_pairs.append((token, value))
                # None means drop (e.g. bare "SET")
            else:
                # Unknown token → title-case
                token_pairs.append((token, token.title()))

        # Stable-sort so adjective/material tokens precede noun tokens.
        token_pairs.sort(key=lambda tv: (0 if tv[0] in _ADJECTIVE_TOKENS else 1))
        words = [v for _, v in token_pairs]

        # Step 4: Assemble result
        if not words and tier is None:
            # Nothing meaningful extracted — return original unchanged
            return item_id

        if tier:
            result = (" ".join(words) + f" T{tier}") if words else f"T{tier}"
        else:
            result = " ".join(words)

        if variant is not None:
            result += f" .{variant}"
        if enchant is not None:
            result += f" +{enchant}"

        return result

    except Exception:
        return item_id

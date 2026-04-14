"""
Furniture catalog and object definitions.
Loads from data/furniture_catalog.json as the single source of truth.
"""
import json
import os
from pathlib import Path

# Resolve catalog path relative to project root
_PROJECT_ROOT = Path(__file__).parent.parent.parent
CATALOG_PATH = _PROJECT_ROOT / "data" / "furniture_catalog.json"


def load_catalog() -> dict:
    """Load and return the furniture catalog."""
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


FURNITURE_CATALOG: dict = load_catalog()
FURNITURE_TYPES: list[str] = list(FURNITURE_CATALOG.keys())


def get_furniture(furniture_type: str) -> dict | None:
    """Return catalog entry for the given furniture type, or None if unknown."""
    return FURNITURE_CATALOG.get(furniture_type.lower().replace(" ", "_"))


def get_aliases() -> dict[str, str]:
    """Return common alias → canonical type mappings."""
    return {
        "couch": "sofa",
        "settee": "sofa",
        "table": "coffee_table",
        "cabinet": "wardrobe",
        "closet": "wardrobe",
        "sideboard": "dresser",
        "tv unit": "tv_stand",
        "media console": "tv_stand",
        "television stand": "tv_stand",
        "bedside table": "nightstand",
        "side table": "nightstand",
        "dining chair": "chair",
        "floor lamp": "lamp",
        "light": "lamp",
        "bookcase": "bookshelf",
    }


def resolve_type(raw: str) -> str:
    """Resolve a raw furniture name (possibly aliased) to a canonical catalog key."""
    normalized = raw.lower().strip().replace(" ", "_")
    aliases = get_aliases()
    # Check direct alias match
    for alias, canonical in aliases.items():
        if alias.replace(" ", "_") == normalized or alias == raw.lower().strip():
            return canonical
    # Check direct catalog match
    if normalized in FURNITURE_CATALOG:
        return normalized
    # Partial match fallback
    for key in FURNITURE_CATALOG:
        if key in normalized or normalized in key:
            return key
    return normalized  # return as-is; let downstream handle the unknown type

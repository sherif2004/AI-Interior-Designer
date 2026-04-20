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
    """Load and return the furniture catalog, handling both dict and list schemas."""
    def _default_catalog() -> dict:
        # Minimal, safe catalog so the server can always boot (used if JSON is missing/corrupt).
        return {
            "sofa": {"id": "sofa", "category": "seating", "description": "Sofa", "size": [2.2, 0.9], "height": 0.85, "color": "#7b8794", "price_low": 300, "price_high": 1800},
            "bed": {"id": "bed", "category": "sleeping", "description": "Bed", "size": [1.6, 2.1], "height": 0.55, "color": "#8d6e63", "price_low": 250, "price_high": 2500},
            "desk": {"id": "desk", "category": "office", "description": "Desk", "size": [1.2, 0.6], "height": 0.75, "color": "#6b7280", "price_low": 80, "price_high": 800},
            "chair": {"id": "chair", "category": "seating", "description": "Chair", "size": [0.5, 0.55], "height": 0.9, "color": "#9aa0a6", "price_low": 30, "price_high": 300},
            "coffee_table": {"id": "coffee_table", "category": "tables", "description": "Coffee table", "size": [1.0, 0.55], "height": 0.45, "color": "#5f6368", "price_low": 40, "price_high": 600},
            "wardrobe": {"id": "wardrobe", "category": "storage", "description": "Wardrobe", "size": [1.2, 0.6], "height": 2.0, "color": "#94a3b8", "price_low": 150, "price_high": 2000},
            "bookshelf": {"id": "bookshelf", "category": "storage", "description": "Bookshelf", "size": [0.8, 0.3], "height": 2.0, "color": "#64748b", "price_low": 50, "price_high": 900},
            "lamp": {"id": "lamp", "category": "lighting", "description": "Lamp", "size": [0.4, 0.4], "height": 1.6, "color": "#f5c842", "price_low": 15, "price_high": 250},
            "rug": {"id": "rug", "category": "decor", "description": "Rug", "size": [2.0, 3.0], "height": 0.02, "color": "#374151", "price_low": 20, "price_high": 600},
            "tv_stand": {"id": "tv_stand", "category": "storage", "description": "TV stand", "size": [1.5, 0.4], "height": 0.5, "color": "#6b7280", "price_low": 60, "price_high": 800},
        }

    try:
        if not CATALOG_PATH.exists() or CATALOG_PATH.stat().st_size < 2:
            return _default_catalog()
        with open(CATALOG_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
            if isinstance(raw, list):
                return {item.get("id"): item for item in raw if isinstance(item, dict) and item.get("id")}
            if isinstance(raw, dict):
                return raw
            return _default_catalog()
    except Exception:
        return _default_catalog()


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

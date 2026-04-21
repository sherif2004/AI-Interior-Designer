"""
Material Store — Phase 4C
==========================
Serves material/texture definitions as a Python data source.
Mirrors the frontend material_library.js data so server-side rendering
and frontend selections are always in sync.
"""

from __future__ import annotations

MATERIALS: dict[str, list[dict]] = {
    "floors": [
        {"id": "oak_wood",          "label": "Oak Wood",            "color": "#c4a882", "pattern": "wood"},
        {"id": "dark_wood",         "label": "Dark Walnut",         "color": "#5c3d2e", "pattern": "wood"},
        {"id": "light_wood",        "label": "Light Birch",         "color": "#e8d5b7", "pattern": "wood"},
        {"id": "herringbone_oak",   "label": "Herringbone Oak",     "color": "#b8976a", "pattern": "herringbone"},
        {"id": "concrete",          "label": "Polished Concrete",   "color": "#9ca3af", "pattern": "concrete"},
        {"id": "marble_white",      "label": "White Marble",        "color": "#f5f5f0", "pattern": "marble"},
        {"id": "marble_dark",       "label": "Noir Marble",         "color": "#2d2d2d", "pattern": "marble"},
        {"id": "terracotta_tile",   "label": "Terracotta Tile",     "color": "#c47a45", "pattern": "tile"},
        {"id": "carpet_grey",       "label": "Grey Carpet",         "color": "#94a3b8", "pattern": "carpet"},
        {"id": "vinyl_white",       "label": "White Vinyl",         "color": "#f8fafc", "pattern": "flat"},
    ],
    "walls": [
        {"id": "plaster_white",       "label": "Warm White",        "color": "#faf9f6"},
        {"id": "plaster_warmgrey",    "label": "Warm Grey",         "color": "#e8e4dc"},
        {"id": "plaster_beige",       "label": "Beige",             "color": "#f0e8d8"},
        {"id": "plaster_sage",        "label": "Sage Green",        "color": "#b5c4b1"},
        {"id": "plaster_blue",        "label": "Dusty Blue",        "color": "#b0c4d8"},
        {"id": "plaster_terracotta",  "label": "Terracotta",        "color": "#d4795a"},
        {"id": "plaster_charcoal",    "label": "Charcoal",          "color": "#374151"},
        {"id": "plaster_navy",        "label": "Navy",              "color": "#1e3a5f"},
        {"id": "brick_exposed",       "label": "Exposed Brick",     "color": "#a05c3c"},
        {"id": "wallpaper_stripe",    "label": "Stripe Wallpaper",  "color": "#e8e0f0"},
        {"id": "wood_panels",         "label": "Wood Panels",       "color": "#8b6344"},
    ],
    "furniture": [
        {"id": "fabric_grey",    "label": "Fabric Grey",     "color": "#6b7280"},
        {"id": "fabric_beige",   "label": "Fabric Beige",    "color": "#d4c5a9"},
        {"id": "fabric_navy",    "label": "Fabric Navy",     "color": "#1e3a5f"},
        {"id": "fabric_olive",   "label": "Fabric Olive",    "color": "#6b7028"},
        {"id": "leather_brown",  "label": "Brown Leather",   "color": "#8b5e3c"},
        {"id": "leather_black",  "label": "Black Leather",   "color": "#1f2937"},
        {"id": "wood_oak",       "label": "Oak",             "color": "#c4a882"},
        {"id": "wood_walnut",    "label": "Walnut",          "color": "#5c3d2e"},
        {"id": "white_gloss",    "label": "White Gloss",     "color": "#f8fafc"},
        {"id": "black_matte",    "label": "Black Matte",     "color": "#111827"},
        {"id": "metal_brushed",  "label": "Brushed Metal",   "color": "#9ca3af"},
    ],
}


def list_materials() -> dict:
    """Return all material categories."""
    return MATERIALS


def get_material(material_id: str) -> dict | None:
    """Look up a material by ID across all categories."""
    for cat, mats in MATERIALS.items():
        for m in mats:
            if m["id"] == material_id:
                return {**m, "category": cat}
    return None

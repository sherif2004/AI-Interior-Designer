"""
Product Search — IKEA Catalog Integration
==========================================
Replaces the original static product_search.py with one that
queries the live scraped IKEA SQLite catalog.

Falls back to the static furniture_catalog.json if the DB doesn't exist yet.

Used by:
    GET /products?q=sofa&budget=800
    GET /products/room
    GET /products/substitute/{furniture_id}
    GET /products/search?q=sofa&budget=800&style=minimalist
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

log = logging.getLogger("product_search")

DATA_DIR    = Path("data")
SQLITE_DB   = DATA_DIR / "ikea_catalog.db"
CATALOG_JSON = DATA_DIR / "furniture_catalog.json"


def _load_fallback_catalog() -> list[dict]:
    """Load the static JSON catalog as fallback."""
    if CATALOG_JSON.exists():
        try:
            raw = json.loads(CATALOG_JSON.read_text())
            return raw if isinstance(raw, list) else raw.get("products", [])
        except Exception:
            pass
    return []


def _db_available() -> bool:
    return SQLITE_DB.exists() and SQLITE_DB.stat().st_size > 1024


# ─── Public API ───────────────────────────────────────────────────────────────

def search_products(
    query:     str   = "",
    category:  str   = "",
    max_price: float = 0,
    min_price: float = 0,
    in_stock:  bool  = True,
    limit:     int   = 20,
) -> list[dict]:
    """
    Search IKEA catalog. Uses SQLite if available, else static JSON.

    Parameters
    ----------
    query     : free-text search (name, series, description)
    category  : RoomState furniture type ("sofa", "bed", "desk", ...)
    max_price : upper price bound (0 = no limit)
    min_price : lower price bound (0 = no limit)
    in_stock  : filter to in-stock items only
    limit     : max results returned
    """
    if _db_available():
        from backend.scraper.catalog_writer import IKEACatalogDB
        db = IKEACatalogDB(SQLITE_DB)
        return db.search(
            query=query,
            category=category,
            max_price=max_price,
            min_price=min_price,
            in_stock=in_stock,
            limit=limit,
        )

    # Fallback: filter static JSON catalog
    log.warning("IKEA SQLite DB not found — using static catalog fallback")
    products = _load_fallback_catalog()
    results  = []

    for p in products:
        if category and p.get("category") != category:
            continue
        if max_price and (p.get("price_high") or 0) > max_price:
            continue
        if min_price and (p.get("price_low") or 0) < min_price:
            continue
        if query:
            q = query.lower()
            searchable = " ".join([
                p.get("name",        ""),
                p.get("series",      ""),
                p.get("description", ""),
            ]).lower()
            if q not in searchable:
                continue
        results.append(p)

    return results[:limit]


def get_product_by_id(item_id: str) -> Optional[dict]:
    """Fetch a single product by ID or IKEA item number."""
    if _db_available():
        from backend.scraper.catalog_writer import IKEACatalogDB
        return IKEACatalogDB(SQLITE_DB).get_by_id(item_id)

    for p in _load_fallback_catalog():
        if p.get("id") == item_id or p.get("item_no") == item_id:
            return p
    return None


def get_products_for_room(room_state: dict) -> list[dict]:
    """
    Return product suggestions for every furniture piece in the room.
    Called by GET /products/room.
    """
    suggestions = []
    for obj in room_state.get("objects", []):
        furniture_type = obj.get("type", "")
        if not furniture_type:
            continue

        price_low  = obj.get("price_low",  0)
        price_high = obj.get("price_high", 0)

        products = search_products(
            category=furniture_type,
            max_price=price_high * 1.2 if price_high else 0,
            in_stock=True,
            limit=5,
        )

        suggestions.append({
            "furniture_id":   obj.get("id"),
            "furniture_type": furniture_type,
            "current_name":   obj.get("name", furniture_type),
            "suggestions":    products,
        })

    return suggestions


def find_substitutes(
    furniture_id: str,
    room_state:   dict,
    max_price:    float = 0,
    limit:        int   = 8,
) -> list[dict]:
    """
    Find alternative products that fit within the spatial slot
    of the current furniture piece. Drives GET /products/substitute/{id}.
    """
    # Find the current piece
    current = next(
        (o for o in room_state.get("objects", []) if o.get("id") == furniture_id),
        None
    )
    if not current:
        return []

    # Spatial slot (with 10% tolerance)
    size = current.get("size", [1.0, 1.0])
    max_w = size[0] * 1.1
    max_d = size[1] * 1.1

    if _db_available():
        from backend.scraper.catalog_writer import IKEACatalogDB
        return IKEACatalogDB(SQLITE_DB).find_alternatives(
            category  = current.get("type", ""),
            max_width = max_w,
            max_depth = max_d,
            max_price = max_price,
            limit     = limit,
        )

    # Fallback
    return search_products(
        category  = current.get("type", ""),
        max_price = max_price,
        limit     = limit,
    )


def catalog_stats() -> dict:
    """Return stats for /health and admin endpoints."""
    if _db_available():
        from backend.scraper.catalog_writer import IKEACatalogDB
        return IKEACatalogDB(SQLITE_DB).catalog_stats()

    products = _load_fallback_catalog()
    from collections import Counter
    cats = Counter(p.get("category", "unknown") for p in products)
    return {
        "total":       len(products),
        "in_stock":    len(products),
        "avg_price_usd": 0,
        "by_category": dict(cats),
        "source":      "static_json",
    }

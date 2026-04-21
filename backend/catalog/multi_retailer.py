"""
Phase 5.2 — Multi-retailer commerce (MVP)
========================================
This is a pragmatic, dependency-free implementation.

- IKEA: uses existing SQLite/JSON integration (product_search.search_products).
- Other retailers: stub providers (return empty until API keys/integrations exist).

The goal is to provide stable API shapes so the frontend can ship now and
providers can be upgraded later without breaking contracts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from backend.catalog.product_search import search_products


@dataclass
class RetailerResult:
    id: str
    name: str
    retailer: str
    price: float | None = None
    currency: str = "USD"
    image_url: str = ""
    buy_url: str = ""
    width_cm: int | None = None
    depth_cm: int | None = None
    height_cm: int | None = None
    in_stock: bool | None = None
    model_url: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "retailer": self.retailer,
            "price": self.price,
            "currency": self.currency,
            "image_url": self.image_url,
            "buy_url": self.buy_url,
            "width_cm": self.width_cm,
            "depth_cm": self.depth_cm,
            "height_cm": self.height_cm,
            "in_stock": self.in_stock,
            "model_url": self.model_url,
        }


def _from_ikea_row(p: dict) -> RetailerResult:
    pid = str(p.get("id") or p.get("item_no") or "")
    return RetailerResult(
        id=pid,
        name=str(p.get("name") or p.get("series") or pid),
        retailer="ikea",
        price=(p.get("price_usd") if isinstance(p.get("price_usd"), (int, float)) else None),
        currency=str(p.get("currency") or "USD").upper(),
        image_url=str(p.get("image_url") or ""),
        buy_url=str(p.get("buy_url") or p.get("url") or ""),
        width_cm=p.get("width_cm"),
        depth_cm=p.get("depth_cm"),
        height_cm=p.get("height_cm"),
        in_stock=p.get("in_stock") if isinstance(p.get("in_stock"), bool) else None,
        model_url=str(p.get("model_url") or ""),
    )


def search_multi_retailer(
    query: str = "",
    style: str = "",
    budget: float = 0,
    retailers: Iterable[str] = ("ikea",),
    limit: int = 50,
) -> list[dict]:
    """
    Return a unified product list across retailers.
    MVP: only IKEA returns real results; others return [].
    """
    retailers_norm = [r.strip().lower() for r in (retailers or []) if str(r).strip()]
    if not retailers_norm:
        retailers_norm = ["ikea"]

    out: list[RetailerResult] = []

    if "ikea" in retailers_norm:
        # IKEA search is already strong; we interpret query as free text.
        rows = search_products(query=query, max_price=budget or 0, limit=min(200, max(1, limit)))
        out.extend(_from_ikea_row(p) for p in (rows or []))

    # Stubs for future integrations; keep stable contract.
    # NOTE: `style` currently unused; providers can implement style-ranking later.
    for r in retailers_norm:
        if r in ("wayfair", "amazon", "west_elm", "westelm"):
            continue

    # De-dupe by (retailer,id)
    seen: set[tuple[str, str]] = set()
    uniq: list[dict] = []
    for p in out:
        key = (p.retailer, p.id)
        if key in seen:
            continue
        seen.add(key)
        uniq.append(p.to_dict())

    return uniq[:limit]


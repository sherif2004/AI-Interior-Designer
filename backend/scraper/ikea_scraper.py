"""
IKEA Furniture Scraper
======================
Uses IKEA's internal search API (sik.search.blue.cdtapps.com) to crawl
all furniture categories and build a complete local catalog.

Usage:
    python -m backend.scraper.ikea_scraper --country us --lang en
    python -m backend.scraper.ikea_scraper --category sofas --limit 100
    python -m backend.scraper.ikea_scraper --full                        # all categories
"""

import asyncio
import json
import logging
import time
import random
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("ikea_scraper")

# ─── Constants ────────────────────────────────────────────────────────────────

BASE_SEARCH_URL = "https://sik.search.blue.cdtapps.com/{cc}/{lang}/search-result-page"
BASE_PRODUCT_URL = "https://www.ikea.com/{cc}/{lang}/p/{slug}-{item_no}/"
BASE_IMAGE_URL   = "https://www.ikea.com/{cc}/{lang}/images/products/{slug}__"

# All IKEA furniture departments with their filter keys
DEPARTMENTS = {
    "sofas":           {"filter": "department:SOF",  "label": "Sofas & armchairs"},
    "beds":            {"filter": "department:BED",  "label": "Beds & bed frames"},
    "mattresses":      {"filter": "department:MAT",  "label": "Mattresses"},
    "wardrobes":       {"filter": "department:WRD",  "label": "Wardrobes"},
    "dressers":        {"filter": "department:DRS",  "label": "Dressers & chests"},
    "dining_tables":   {"filter": "department:TBL",  "label": "Dining tables"},
    "chairs":          {"filter": "department:CHR",  "label": "Dining chairs"},
    "desks":           {"filter": "department:DSK",  "label": "Desks"},
    "office_chairs":   {"filter": "department:OCH",  "label": "Office chairs"},
    "bookshelves":     {"filter": "department:SHL",  "label": "Bookcases & shelving"},
    "coffee_tables":   {"filter": "department:CTB",  "label": "Coffee & side tables"},
    "tv_benches":      {"filter": "department:TVB",  "label": "TV & media furniture"},
    "lamps":           {"filter": "department:LMP",  "label": "Floor & table lamps"},
    "rugs":            {"filter": "department:RUG",  "label": "Rugs"},
    "nightstands":     {"filter": "department:NST",  "label": "Bedside tables"},
    "room_dividers":   {"filter": "department:RDV",  "label": "Room dividers"},
    "plants":          {"filter": "department:PLT",  "label": "Plants & plant pots"},
    "mirrors":         {"filter": "department:MIR",  "label": "Mirrors"},
    "cabinets":        {"filter": "department:CAB",  "label": "Cabinets & cupboards"},
    "benches":         {"filter": "department:BNC",  "label": "Benches"},
    "stools":          {"filter": "department:STL",  "label": "Bar stools & stools"},
    "outdoor":         {"filter": "department:OUT",  "label": "Outdoor furniture"},
    "kids_beds":       {"filter": "department:KBD",  "label": "Children's beds"},
    "kids_desks":      {"filter": "department:KDS",  "label": "Children's desks"},
}

# Map IKEA category → RoomState furniture type
CATEGORY_MAP = {
    "sofas":         "sofa",
    "beds":          "bed",
    "mattresses":    "mattress",
    "wardrobes":     "wardrobe",
    "dressers":      "dresser",
    "dining_tables": "dining_table",
    "chairs":        "chair",
    "desks":         "desk",
    "office_chairs": "office_chair",
    "bookshelves":   "bookshelf",
    "coffee_tables": "coffee_table",
    "tv_benches":    "tv_stand",
    "lamps":         "lamp",
    "rugs":          "rug",
    "nightstands":   "nightstand",
    "room_dividers": "room_divider",
    "plants":        "plant",
    "mirrors":       "mirror",
    "cabinets":      "cabinet",
    "benches":       "bench",
    "stools":        "bar_stool",
    "kids_beds":     "single_bed",
}

# Default dimensions per category (meters) — used when not found in API
DEFAULT_DIMS = {
    "sofa":          {"w": 2.2, "d": 0.9, "h": 0.85},
    "bed":           {"w": 1.6, "d": 2.1, "h": 0.5},
    "mattress":      {"w": 1.6, "d": 2.0, "h": 0.25},
    "wardrobe":      {"w": 1.2, "d": 0.6, "h": 2.0},
    "dresser":       {"w": 0.8, "d": 0.45, "h": 1.1},
    "dining_table":  {"w": 1.4, "d": 0.85, "h": 0.75},
    "chair":         {"w": 0.5, "d": 0.55, "h": 0.9},
    "desk":          {"w": 1.2, "d": 0.6, "h": 0.75},
    "office_chair":  {"w": 0.65, "d": 0.65, "h": 1.1},
    "bookshelf":     {"w": 0.8, "d": 0.3, "h": 2.0},
    "coffee_table":  {"w": 1.0, "d": 0.55, "h": 0.45},
    "tv_stand":      {"w": 1.5, "d": 0.4, "h": 0.5},
    "lamp":          {"w": 0.4, "d": 0.4, "h": 1.6},
    "rug":           {"w": 2.0, "d": 3.0, "h": 0.02},
    "nightstand":    {"w": 0.5, "d": 0.4, "h": 0.6},
    "room_divider":  {"w": 1.6, "d": 0.05, "h": 1.8},
    "plant":         {"w": 0.3, "d": 0.3, "h": 0.8},
    "mirror":        {"w": 0.6, "d": 0.05, "h": 1.5},
    "cabinet":       {"w": 0.8, "d": 0.4, "h": 1.2},
    "bench":         {"w": 1.2, "d": 0.35, "h": 0.45},
    "bar_stool":     {"w": 0.4, "d": 0.4, "h": 0.75},
    "single_bed":    {"w": 0.9, "d": 2.0, "h": 0.45},
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept":           "application/json, text/plain, */*",
    "Accept-Language":  "en-US,en;q=0.9",
    "Accept-Encoding":  "gzip, deflate, br",
    "Referer":          "https://www.ikea.com/",
    "Origin":           "https://www.ikea.com",
    "sec-ch-ua":        '"Chromium";v="122", "Not(A:Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-fetch-dest":   "empty",
    "sec-fetch-mode":   "cors",
    "sec-fetch-site":   "cross-site",
}


# ─── Data Models ──────────────────────────────────────────────────────────────

@dataclass
class IKEAProduct:
    """Normalized IKEA product matching the project's catalog schema."""
    # Identity
    item_no:      str = ""
    name:         str = ""
    description:  str = ""
    url:          str = ""

    # Categorization
    category:     str = ""          # RoomState furniture type (e.g. "sofa")
    ikea_category: str = ""         # Raw IKEA category (e.g. "sofas")
    series:       str = ""          # e.g. "EKTORP", "KALLAX"

    # Dimensions (meters)
    width:        float = 0.0
    depth:        float = 0.0
    height:       float = 0.0

    # Pricing (USD)
    price:        float = 0.0
    price_low:    float = 0.0
    price_high:   float = 0.0
    currency:     str = "USD"

    # Physical
    weight_kg:    float = 0.0
    color:        str = ""
    material:     str = ""
    colors:       list = field(default_factory=list)  # all available colors

    # Spatial rules (meters)
    min_clearance: float = 0.6

    # Commerce
    in_stock:     bool = True
    image_url:    str = ""
    image_urls:   list = field(default_factory=list)
    buy_url:      str = ""

    # Source metadata
    source:       str = "ikea"
    scraped_at:   str = ""


# ─── Parser ───────────────────────────────────────────────────────────────────

class IKEAResponseParser:
    """Parses raw IKEA search API response into IKEAProduct objects."""

    @staticmethod
    def parse_dimensions(raw: dict) -> tuple[float, float, float]:
        """Extract (width, depth, height) in meters from IKEA measurement blocks."""
        measurements = raw.get("measurements", {})
        if not measurements:
            return 0.0, 0.0, 0.0

        def to_meters(val: float, unit: str) -> float:
            if not val:
                return 0.0
            unit = (unit or "cm").lower()
            if unit == "cm":
                return round(val / 100, 3)
            if unit == "mm":
                return round(val / 1000, 3)
            return round(float(val), 3)   # assume meters

        dims = {}
        for block in measurements.get("dimensionMeasurements", []):
            dim_type  = (block.get("type")  or "").lower()
            dim_value = block.get("value", 0)
            dim_unit  = block.get("unit",  "cm")
            if "width"  in dim_type:   dims["w"] = to_meters(dim_value, dim_unit)
            if "depth"  in dim_type:   dims["d"] = to_meters(dim_value, dim_unit)
            if "height" in dim_type:   dims["h"] = to_meters(dim_value, dim_unit)
            if "length" in dim_type:   dims["d"] = to_meters(dim_value, dim_unit)
            if "diameter" in dim_type: dims["w"] = dims["d"] = to_meters(dim_value, dim_unit)

        return dims.get("w", 0.0), dims.get("d", 0.0), dims.get("h", 0.0)

    @staticmethod
    def parse_price(raw: dict) -> tuple[float, float, float]:
        """Return (price, price_low, price_high)."""
        price_obj = raw.get("salesPrice", {}) or raw.get("price", {})
        if not price_obj:
            return 0.0, 0.0, 0.0

        price = float(price_obj.get("numeral", 0) or 0)

        # Check for range pricing (e.g. sectional sofas)
        low  = float(price_obj.get("lowerBound", price) or price)
        high = float(price_obj.get("upperBound", price) or price)

        if low == high == 0:
            low = high = price

        return price, low, high

    @staticmethod
    def parse_currency(raw: dict) -> str:
        """
        Best-effort currency extraction. IKEA payloads commonly include:
          salesPrice.currencyCode or price.currencyCode
        Falls back to "USD" to preserve legacy behavior.
        """
        price_obj = raw.get("salesPrice", {}) or raw.get("price", {}) or {}
        for key in ("currencyCode", "currency", "currency_code"):
            cur = price_obj.get(key)
            if isinstance(cur, str) and cur.strip():
                return cur.strip().upper()
        return "USD"

    @staticmethod
    def parse_images(raw: dict, cc: str, lang: str) -> tuple[str, list]:
        """Return (primary_image_url, all_image_urls)."""
        images = raw.get("images", []) or []
        urls   = []

        for img in images:
            src = (
                img.get("href")
                or img.get("url")
                or img.get("src")
                or ""
            )
            if src and src not in urls:
                urls.append(src)

        # Fallback: construct from product ID
        if not urls:
            item_no = str(raw.get("id", "") or "").replace(".", "")
            if item_no:
                # Country/lang is not always required for image CDN paths, but keep it consistent.
                # This fallback is mostly used when the API doesn't include images.
                cc = (cc or "us").strip().lower()
                lang = (lang or "en").strip().lower()
                urls = [f"https://www.ikea.com/{cc}/{lang}/images/products/{item_no}__main.jpg"]

        return (urls[0] if urls else ""), urls

    @classmethod
    def parse_product(cls, raw: dict, category_key: str, cc: str, lang: str) -> IKEAProduct:
        """Convert one raw IKEA API product dict into an IKEAProduct."""
        from datetime import datetime, timezone

        item_no     = str(raw.get("id", "") or "").replace(".", "")
        name        = raw.get("name", "")         or ""
        description = raw.get("typeName", "")     or ""
        series      = (name.split(" ")[0] if name else "").upper()

        # Dimensions
        w, d, h = cls.parse_dimensions(raw)
        furniture_type = CATEGORY_MAP.get(category_key, category_key)

        # Fall back to defaults if dimensions missing
        defaults = DEFAULT_DIMS.get(furniture_type, {"w": 0.5, "d": 0.5, "h": 1.0})
        w = w or defaults["w"]
        d = d or defaults["d"]
        h = h or defaults["h"]

        # Price
        price, price_low, price_high = cls.parse_price(raw)
        currency = cls.parse_currency(raw)

        # Images
        primary_img, all_imgs = cls.parse_images(raw, cc=cc, lang=lang)

        # Color
        main_color_block = raw.get("mainImageAlt", "") or ""
        color = raw.get("contextualImageAlt", "") or main_color_block

        # Stock
        stock = raw.get("availability", {}) or {}
        in_stock = stock.get("available", True)

        # URL
        pip = (raw.get("pipUrl", "") or "").strip()
        if pip.startswith("http://") or pip.startswith("https://"):
            buy_url = pip
        elif pip.startswith("/"):
            buy_url = "https://www.ikea.com" + pip
        elif pip:
            # pipUrl is usually a path like "some-product-name-12345678/"
            buy_url = f"https://www.ikea.com/{cc}/{lang}/p/{pip.strip('/')}/"
        else:
            buy_url = f"https://www.ikea.com/{cc}/{lang}/search/?q={item_no}"

        # Clean up accidental double prefixes if source already included "/{cc}/{lang}/p/"
        buy_url = buy_url.replace("https://www.ikea.com/https://www.ikea.com/", "https://www.ikea.com/")

        # Min clearance heuristic: larger furniture needs more walkway
        size_metric = max(w, d)
        min_clearance = 0.9 if size_metric > 1.5 else 0.6

        return IKEAProduct(
            item_no=item_no,
            name=name,
            description=description,
            url=buy_url,
            category=furniture_type,
            ikea_category=category_key,
            series=series,
            width=round(w, 3),
            depth=round(d, 3),
            height=round(h, 3),
            price=price,
            price_low=price_low,
            price_high=price_high,
            currency=currency,
            weight_kg=float(raw.get("weight", 0) or 0),
            color=color,
            colors=[color] if color else [],
            min_clearance=min_clearance,
            in_stock=bool(in_stock),
            image_url=primary_img,
            image_urls=all_imgs,
            buy_url=buy_url,
            scraped_at=datetime.now(timezone.utc).isoformat(),
        )


# ─── Rate Limiter ─────────────────────────────────────────────────────────────

class RateLimiter:
    """Token bucket: max `rate` requests per second."""
    def __init__(self, rate: float = 2.0):
        self.rate      = rate
        self.min_wait  = 1.0 / rate
        self._last     = 0.0

    async def wait(self):
        now    = time.monotonic()
        wait   = self.min_wait - (now - self._last)
        jitter = random.uniform(0.1, 0.4)   # polite jitter
        if wait > 0:
            await asyncio.sleep(wait + jitter)
        else:
            await asyncio.sleep(jitter)
        self._last = time.monotonic()


# ─── Core Scraper ─────────────────────────────────────────────────────────────

class IKEAScraper:
    """
    Async scraper for IKEA's internal search API.

    Parameters
    ----------
    cc      : ISO country code  (default: "us")
    lang    : language code     (default: "en")
    rate    : requests/sec      (default: 2.0 — polite)
    page_sz : products per page (default: 24 — IKEA max)
    """

    def __init__(
        self,
        cc:      str   = "us",
        lang:    str   = "en",
        rate:    float = 2.0,
        page_sz: int   = 24,
    ):
        self.cc      = cc
        self.lang    = lang
        self.page_sz = page_sz
        self.limiter = RateLimiter(rate)
        self.parser  = IKEAResponseParser()
        self._url    = BASE_SEARCH_URL.format(cc=cc, lang=lang)

    # ── HTTP ──────────────────────────────────────────────────────────────────

    async def _get(self, client: httpx.AsyncClient, params: dict) -> dict:
        """Single request with retry on 429 / 5xx."""
        for attempt in range(4):
            await self.limiter.wait()
            try:
                r = await client.get(self._url, params=params, headers=HEADERS, timeout=20)
                if r.status_code == 200:
                    return r.json()
                if r.status_code == 429:
                    wait = 10 * (attempt + 1)
                    log.warning(f"Rate limited. Waiting {wait}s …")
                    await asyncio.sleep(wait)
                    continue
                if r.status_code >= 500:
                    await asyncio.sleep(5 * (attempt + 1))
                    continue
                log.warning(f"HTTP {r.status_code} for params={params}")
                return {}
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                log.warning(f"Request error (attempt {attempt+1}): {e}")
                await asyncio.sleep(3 * (attempt + 1))
        return {}

    # ── Category Scraper ──────────────────────────────────────────────────────

    async def scrape_category(
        self,
        client:       httpx.AsyncClient,
        category_key: str,
        max_products: int = 500,
    ) -> list[IKEAProduct]:
        """Scrape all pages of one IKEA department."""
        dept_info = DEPARTMENTS.get(category_key)
        if not dept_info:
            log.error(f"Unknown category: {category_key}")
            return []

        products = []
        start    = 0
        total    = None

        log.info(f"[{category_key}] Starting — {dept_info['label']}")

        while True:
            params = {
                "types": "PRODUCT",
                "q":     dept_info.get("label", category_key),
            }
            data = await self._get(client, params)
            if not data:
                break

            # Navigate IKEA's response tree
            page      = data.get("searchResultPage", {})
            prod_data = page.get("products", {}).get("main", {})
            items     = prod_data.get("items", [])

            if total is None:
                total = prod_data.get("totalCount", 0)
                log.info(f"[{category_key}] Total products: {total}")

            if not items:
                break

            for item in items:
                raw = item.get("product", {})
                if raw:
                    try:
                        p = self.parser.parse_product(raw, category_key, self.cc, self.lang)
                        if p.item_no:   # skip if no ID
                            products.append(p)
                    except Exception as e:
                        log.debug(f"Parse error for item: {e}")

            start += len(items)
            log.info(f"[{category_key}] Fetched {len(products)}/{min(total or 0, max_products)}")

            if start >= min(total or 0, max_products) or not items:
                break

        log.info(f"[{category_key}] Done — {len(products)} products")
        return products

    # ── Search ────────────────────────────────────────────────────────────────

    async def search(
        self,
        client:  httpx.AsyncClient,
        query:   str,
        limit:   int = 48,
    ) -> list[IKEAProduct]:
        """Search across all categories for a keyword."""
        products = []
        start    = 0

        while start < limit:
            params = {
                "types": "PRODUCT",
                "q":     query,
            }
            data  = await self._get(client, params)
            page  = data.get("searchResultPage", {})
            items = page.get("products", {}).get("main", {}).get("items", [])

            if not items:
                break

            for item in items:
                raw = item.get("product", {})
                if raw:
                    # Infer category from typeName
                    type_name = (raw.get("typeName", "") or "").lower()
                    cat = next(
                        (k for k, v in CATEGORY_MAP.items() if k in type_name),
                        "furniture"
                    )
                    try:
                        products.append(self.parser.parse_product(raw, cat, self.cc, self.lang))
                    except Exception:
                        pass

            start += len(items)

        return products

    # ── Full Catalog ──────────────────────────────────────────────────────────

    async def scrape_all(
        self,
        categories:    list[str] | None = None,
        max_per_cat:   int  = 500,
        max_total:     int  = 10_000,
    ) -> list[IKEAProduct]:
        """Scrape all (or selected) categories. Returns deduplicated product list."""
        cats    = categories or list(DEPARTMENTS.keys())
        all_p   = []
        seen    = set()

        async with httpx.AsyncClient(follow_redirects=True) as client:
            for cat in cats:
                if len(all_p) >= max_total:
                    break
                products = await self.scrape_category(
                    client, cat, max_products=max_per_cat
                )
                for p in products:
                    if p.item_no not in seen:
                        seen.add(p.item_no)
                        all_p.append(p)

        log.info(f"Scrape complete — {len(all_p)} unique products across {len(cats)} categories")
        return all_p

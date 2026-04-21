"""
IKEA 3D Model URL Fetcher
=========================
Uses Playwright to intercept network requests on IKEA product pages
and capture the GLB/glTF 3D model URLs served by IKEA's model viewer.

This is a separate enrichment step that runs AFTER the main scraper.
It updates the `model_url` column in ikea_catalog.db for products
that have a 3D viewer on their product page.

IMPORTANT: This uses IKEA's website as a personal/portfolio feature.
           Respect IKEA's ToS for commercial use.

Usage:
    python -m backend.scraper.ikea_model_fetcher --limit 100
    python -m backend.scraper.ikea_model_fetcher --category sofa --limit 50
    python -m backend.scraper.ikea_model_fetcher --all
"""

import asyncio
import json
import logging
import re
import sqlite3
import time
from pathlib import Path

log = logging.getLogger("ikea_model_fetcher")

DATA_DIR  = Path("data")
SQLITE_DB = DATA_DIR / "ikea_catalog.db"

# Patterns that identify 3D model assets from IKEA's CDN
GLB_PATTERNS = [
    re.compile(r"https://asset\.inter\.ikea\.com/[^\"'\s]+\.glb", re.I),
    re.compile(r"https://[^\"'\s]+/models/[^\"'\s]+\.glb", re.I),
    re.compile(r"https://[^\"'\s]+\.gltf", re.I),
    re.compile(r"https://[^\"'\s]+/3d/[^\"'\s]+", re.I),
]


async def fetch_model_url(page, pip_url: str, timeout: int = 15000) -> str:
    """
    Load a product page and capture any GLB model URL from network traffic.
    Returns the first matched GLB URL, or empty string if none found.
    """
    captured: list[str] = []

    def on_request(request):
        url = request.url
        for pat in GLB_PATTERNS:
            if pat.search(url):
                captured.append(url)
                break

    def on_response(response):
        url = response.url
        for pat in GLB_PATTERNS:
            if pat.search(url):
                captured.append(url)
                break

    page.on("request", on_request)
    page.on("response", on_response)

    try:
        await page.goto(pip_url, wait_until="domcontentloaded", timeout=timeout)
        # Wait briefly for any lazy-loaded 3D viewer to initialize
        await page.wait_for_timeout(3000)

        # Also check page source for embedded model URLs
        content = await page.content()
        for pat in GLB_PATTERNS:
            match = pat.search(content)
            if match:
                captured.append(match.group(0))

    except Exception as e:
        log.debug(f"Error loading {pip_url}: {e}")
    finally:
        page.remove_listener("request", on_request)
        page.remove_listener("response", on_response)

    # Return first unique GLB URL found
    seen = set()
    for url in captured:
        clean = url.strip().rstrip("\"',")
        if clean and clean not in seen:
            seen.add(clean)
            if ".glb" in clean or ".gltf" in clean:
                return clean

    return ""


def get_products_without_model(
    db_path: Path = SQLITE_DB,
    category: str = "",
    limit: int = 100,
) -> list[dict]:
    """Fetch products from DB that don't have a model_url yet."""
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    where = "(model_url IS NULL OR model_url = '')"
    params: list = []

    if category:
        where += " AND category = ?"
        params.append(category)

    sql = f"SELECT id, item_no, name, buy_url FROM products WHERE {where} ORDER BY price DESC LIMIT ?"
    params.append(limit)

    rows = cur.execute(sql, params).fetchall()
    con.close()
    return [dict(r) for r in rows]


def update_model_url(db_path: Path, product_id: str, model_url: str):
    """Update a single product's model_url in the database."""
    con = sqlite3.connect(db_path)
    con.execute(
        "UPDATE products SET model_url = ? WHERE id = ?",
        (model_url, product_id)
    )
    con.commit()
    con.close()


async def enrich_models(
    db_path: Path = SQLITE_DB,
    category: str = "",
    limit: int = 100,
    concurrency: int = 2,
    headless: bool = True,
):
    """
    Main enrichment loop. Spawns Playwright browser, visits each product page,
    captures GLB URL, writes back to DB.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        log.error("Playwright not installed. Run: pip install playwright && playwright install chromium")
        return

    products = get_products_without_model(db_path, category=category, limit=limit)
    if not products:
        log.info("All products already have model URLs (or DB is empty).")
        return

    log.info(f"Fetching 3D model URLs for {len(products)} products (concurrency={concurrency})")

    found    = 0
    not_found = 0

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=headless)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            locale="en-US",
            viewport={"width": 1280, "height": 800},
        )

        # Semaphore for controlled concurrency
        sem = asyncio.Semaphore(concurrency)

        async def process_product(p: dict):
            nonlocal found, not_found
            async with sem:
                page = await context.new_page()
                try:
                    pip_url = p.get("buy_url", "")
                    if not pip_url:
                        return

                    log.info(f"  [{p['name']}] {pip_url[:80]}...")
                    model_url = await fetch_model_url(page, pip_url)

                    if model_url:
                        log.info(f"  ✅ Found GLB: {model_url[:80]}")
                        update_model_url(db_path, p["id"], model_url)
                        found += 1
                    else:
                        log.debug(f"  ❌ No 3D model for {p['name']}")
                        not_found += 1

                    # Polite delay
                    await asyncio.sleep(1.5)
                except Exception as e:
                    log.warning(f"  Error processing {p.get('name', '?')}: {e}")
                    not_found += 1
                finally:
                    await page.close()

        tasks = [process_product(p) for p in products]
        await asyncio.gather(*tasks)
        await browser.close()

    log.info(f"\n{'='*50}")
    log.info(f"Model fetching complete: {found} found, {not_found} not found")
    log.info(f"{'='*50}")


def main():
    import argparse
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    p = argparse.ArgumentParser(description="IKEA 3D Model URL Fetcher")
    p.add_argument("--limit",       type=int, default=100,  help="Max products to process")
    p.add_argument("--category",    type=str, default="",   help="Only process this RoomState category")
    p.add_argument("--all",         action="store_true",    help="Process all products (ignores --limit)")
    p.add_argument("--concurrency", type=int, default=2,    help="Parallel browser pages")
    p.add_argument("--visible",     action="store_true",    help="Show browser window (non-headless)")
    args = p.parse_args()

    limit = 99999 if args.all else args.limit

    asyncio.run(enrich_models(
        db_path=SQLITE_DB,
        category=args.category,
        limit=limit,
        concurrency=args.concurrency,
        headless=not args.visible,
    ))


if __name__ == "__main__":
    main()

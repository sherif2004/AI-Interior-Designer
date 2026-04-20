"""
Playwright Visual Navigation Scraper
====================================
A heavily-armored headless visual scraper that extracts furniture data
from DOM layouts rather than hidden HTTP endpoints.
Immune to strict API parameter deprecations.
"""

import asyncio
import logging
from datetime import datetime, timezone

from playwright.async_api import async_playwright
from .ikea_scraper import IKEAProduct, CATEGORY_MAP

log = logging.getLogger("playwright_scraper")


class VisualScraper:
    def __init__(self, cc="us", lang="en", headless=True):
        self.cc = cc
        self.lang = lang
        self.headless = headless
        self.base_url = f"https://www.ikea.com/{cc}/{lang}/search/?q="

    async def scrape(self, query: str, limit: int = 24) -> list[IKEAProduct]:
        """Navigate to IKEA Search, parse grid elements visually."""
        
        log.info(f"[Playwright] Launching Chrome engine for query: '{query}'")
        products = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            url = self.base_url + query.replace(" ", "+")
            log.info(f"Navigating -> {url}")
            
            try:
                # Wait until the network is idle or DOM is loaded
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                
                # Wait for the product grid containers to physically render
                # 'plp-fragment-wrapper' is a common IKEA react node for items
                await page.wait_for_selector(".plp-fragment-wrapper", timeout=15000)
                
                # Scroll slightly to trigger image loading
                await page.mouse.wheel(0, 1500)
                await asyncio.sleep(1)
                
                elements = await page.query_selector_all(".plp-fragment-wrapper")
                log.info(f"Visual Engine detected {len(elements)} physical DOM grid nodes.")
                
            except Exception as e:
                log.error(f"[Playwright] Page load/selector timeout: {e}")
                elements = []

            for grid_node in elements[:limit]:
                try:
                    # 1. Title/Name
                    name_el = await grid_node.query_selector(".pip-header-section__title--small")
                    name = await name_el.inner_text() if name_el else ""

                    # 2. Description
                    desc_el = await grid_node.query_selector(".pip-header-section__description-text")
                    desc = await desc_el.inner_text() if desc_el else ""

                    # 3. Price
                    price_el = await grid_node.query_selector(".pip-price__integer")
                    price_str = await price_el.inner_text() if price_el else "0"
                    price = float(price_str.replace("$", "").replace(",", "").strip() or 0)

                    # 4. URL
                    link_el = await grid_node.query_selector("a")
                    buy_url = await link_el.get_attribute("href") if link_el else ""

                    # 5. Image
                    img_el = await grid_node.query_selector("img")
                    img_url = await img_el.get_attribute("src") if img_el else ""

                    item_no = buy_url.split("-")[-1].replace("/", "") if buy_url else f"mock_{len(products)}"
                    
                    category = "furniture"
                    for k, v in CATEGORY_MAP.items():
                        if k in desc.lower():
                            category = v

                    if name:
                        product = IKEAProduct(
                            item_no=item_no,
                            name=name.strip(),
                            description=desc.strip(),
                            category=category,
                            ikea_category="visual_scrape",
                            series=name.split(" ")[0].upper(),
                            price=price,
                            price_low=price,
                            price_high=price,
                            width=1.0,  # Defaulting dimensions since visual grid doesn't always show them
                            depth=1.0,
                            height=1.0,
                            min_clearance=0.8,
                            image_url=img_url,
                            buy_url=buy_url,
                            scraped_at=datetime.now(timezone.utc).isoformat()
                        )
                        products.append(product)

                except Exception as e:
                    # Stale element or DOM mismatch
                    log.debug(f"[Playwright] DOM read error on node: {e}")

            await browser.close()
            
        log.info(f"[Playwright] Successfully extracted {len(products)} models via optical processing.")
        return products

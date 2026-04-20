"""
IKEA Scraper — CLI Runner
=========================

Usage examples:
    # Scrape sofas only (fast test)
    python -m backend.scraper.run_scraper --category sofas

    # Scrape specific categories
    python -m backend.scraper.run_scraper --categories sofas beds desks chairs

    # Full catalog (~10k products, ~30 min)
    python -m backend.scraper.run_scraper --full

    # With custom rate limit (slower = safer)
    python -m backend.scraper.run_scraper --full --rate 1.0

    # Different country/language
    python -m backend.scraper.run_scraper --full --country gb --lang en

    # Update existing catalog (re-scrape all, keep fresh)
    python -m backend.scraper.run_scraper --full --update

    # Search mode (quick lookup)
    python -m backend.scraper.run_scraper --search "KALLAX"
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

# ensure project root on path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.scraper.ikea_scraper import IKEAScraper, DEPARTMENTS
from backend.scraper.catalog_writer import save_ikea_json, merge_into_project_catalog, save_sqlite

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("run_scraper")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="IKEA furniture catalog scraper")

    # Target selection
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--full",       action="store_true",  help="Scrape all categories")
    group.add_argument("--category",   type=str,             help=f"Single category. Options: {list(DEPARTMENTS)}")
    group.add_argument("--categories", nargs="+",            help="Multiple categories")
    group.add_argument("--search",     type=str,             help="Search query (quick mode)")

    # Options
    p.add_argument("--country",   default="us",    help="Country code (default: us)")
    p.add_argument("--lang",      default="en",    help="Language code (default: en)")
    p.add_argument("--rate",      type=float, default=2.0, help="Requests/sec (default: 2.0)")
    p.add_argument("--limit",     type=int,   default=500, help="Max products per category (default: 500)")
    p.add_argument("--max-total", type=int,   default=10_000, help="Max total products (default: 10000)")
    p.add_argument("--no-sqlite", action="store_true",  help="Skip SQLite save")
    p.add_argument("--no-merge",  action="store_true",  help="Skip merging into furniture_catalog.json")
    p.add_argument("--update",    action="store_true",  help="Force re-scrape even if data exists")
    p.add_argument("--output",    type=str, default=None, help="Custom output JSON path")

    return p.parse_args()


async def run(args: argparse.Namespace):
    scraper = IKEAScraper(
        cc=args.country,
        lang=args.lang,
        rate=args.rate,
    )

    # ── Determine what to scrape ──────────────────────────────────────────────
    import httpx

    if args.full:
        log.info(f"Full catalog scrape — {len(DEPARTMENTS)} categories, up to {args.max_total} products")
        log.info("Estimated time: 20–40 minutes at default rate. Use Ctrl+C to stop early.")
        products = await scraper.scrape_all(
            max_per_cat=args.limit,
            max_total=args.max_total,
        )

    elif args.category:
        if args.category not in DEPARTMENTS:
            log.error(f"Unknown category '{args.category}'. Available: {list(DEPARTMENTS.keys())}")
            sys.exit(1)
        log.info(f"Scraping category: {args.category}")
        async with httpx.AsyncClient(follow_redirects=True) as client:
            products = await scraper.scrape_category(
                client, args.category, max_products=args.limit
            )

    elif args.categories:
        unknown = [c for c in args.categories if c not in DEPARTMENTS]
        if unknown:
            log.error(f"Unknown categories: {unknown}. Available: {list(DEPARTMENTS.keys())}")
            sys.exit(1)
        log.info(f"Scraping {len(args.categories)} categories: {args.categories}")
        products = await scraper.scrape_all(
            categories=args.categories,
            max_per_cat=args.limit,
            max_total=args.max_total,
        )

    elif args.search:
        log.info(f"Searching: '{args.search}'")
        async with httpx.AsyncClient(follow_redirects=True) as client:
            products = await scraper.search(client, args.search, limit=48)

    # ── Save ──────────────────────────────────────────────────────────────────
    if not products:
        log.warning("No products scraped.")
        return

    log.info(f"\n{'='*50}")
    log.info(f"Scraped {len(products)} products")
    log.info(f"{'='*50}")

    # Print category breakdown
    from collections import Counter
    counts = Counter(p.ikea_category for p in products)
    for cat, n in counts.most_common():
        log.info(f"  {cat:<25} {n:>5} products")

    # Primary IKEA JSON
    out_path = Path(args.output) if args.output else None
    if out_path:
        import dataclasses
        data = [dataclasses.asdict(p) for p in products]
        out_path.write_text(json.dumps(data, indent=2))
        log.info(f"Saved → {out_path}")
    else:
        save_ikea_json(products)

    # SQLite
    if not args.no_sqlite:
        save_sqlite(products)

    # Merge into project catalog
    if not args.no_merge:
        merge_into_project_catalog(products)

    log.info("\nDone. Next steps:")
    log.info("  1. Review data/ikea_catalog.json")
    log.info("  2. Run: python -m backend.scraper.run_scraper --search KALLAX  (quick test)")
    log.info("  3. Update backend/catalog/product_search.py to query IKEACatalogDB")


def main():
    args = parse_args()
    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        log.info("\nInterrupted — partial results may have been saved.")


if __name__ == "__main__":
    main()

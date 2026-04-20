"""
IKEA Catalog API Endpoints
===========================
Add these routes to backend/api/server.py

from backend.api.ikea_routes import router as ikea_router
app.include_router(ikea_router, prefix="")
"""

from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional
from pathlib import Path
import asyncio
import time
import uuid

from backend.catalog.product_search import (
    search_products,
    get_product_by_id,
    get_products_for_room,
    find_substitutes,
    catalog_stats,
)

router = APIRouter(tags=["IKEA Catalog"])

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
SQLITE_DB = DATA_DIR / "ikea_catalog.db"
IKEA_JSON = DATA_DIR / "ikea_catalog.json"

# In-memory job registry (good enough for single-process dev server)
_SCRAPE_JOBS: dict[str, dict] = {}
_SCRAPE_LOCK = asyncio.Lock()

def _fx_rate(from_cur: str, to_cur: str) -> float | None:
    """
    Simple env-driven FX conversion. Example:
      FX_USD_TO_EGP=48.0
    """
    import os
    from_cur = (from_cur or "").upper()
    to_cur = (to_cur or "").upper()
    if not from_cur or not to_cur or from_cur == to_cur:
        return 1.0
    key = f"FX_{from_cur}_TO_{to_cur}"
    try:
        v = float(os.getenv(key, "") or "")
        return v if v > 0 else None
    except Exception:
        return None

def _convert_money(amount: float | None, from_cur: str, to_cur: str) -> float | None:
    if amount is None:
        return None
    r = _fx_rate(from_cur, to_cur)
    if r is None:
        return None
    return round(float(amount) * float(r), 2)

def _normalize_product(p: dict) -> dict:
    """
    Normalize product fields across DB/JSON sources so the frontend can rely on:
      - id (string)
      - price_usd (number)
      - width_cm/depth_cm/height_cm (numbers, optional)
      - image_url, buy_url
    """
    item_no = p.get("id") or p.get("item_no") or p.get("article_number") or p.get("sku")
    out = dict(p)
    if item_no and not out.get("id"):
        out["id"] = str(item_no)

    # Price normalization
    if out.get("price_usd") is None:
        price = out.get("price")
        if isinstance(price, (int, float)):
            out["price_usd"] = float(price)
        elif isinstance(out.get("price_low"), (int, float)):
            out["price_usd"] = float(out["price_low"])

    if isinstance(out.get("currency"), str) and out["currency"].strip():
        out["currency"] = out["currency"].strip().upper()
    elif out.get("currency") is None:
        out["currency"] = "USD"

    # Dimension normalization: support both meters (width/depth/height) and cm fields.
    def _m_to_cm(v):
        try:
            fv = float(v)
            return int(round(fv * 100))
        except Exception:
            return None

    if out.get("width_cm") is None and out.get("width") is not None:
        out["width_cm"] = _m_to_cm(out.get("width"))
    if out.get("depth_cm") is None and out.get("depth") is not None:
        out["depth_cm"] = _m_to_cm(out.get("depth"))
    if out.get("height_cm") is None and out.get("height") is not None:
        out["height_cm"] = _m_to_cm(out.get("height"))

    # URL aliases
    if out.get("buy_url") is None and out.get("url"):
        out["buy_url"] = out.get("url")

    # Ensure buy_url is absolute so frontend "View" doesn't hit our own server.
    bu = out.get("buy_url")
    if isinstance(bu, str):
        bu = bu.strip()
        # Fix accidentally duplicated IKEA prefixes (legacy scraped data)
        # Example: "https://www.ikea.com/us/en/p/https://www.ikea.com/us/en/p/xyz/"
        marker = "https://www.ikea.com/"
        if bu.count(marker) >= 2:
            bu = marker + bu.split(marker)[-1]
        if bu.startswith("//"):
            bu = "https:" + bu
        elif bu.startswith("/"):
            bu = "https://www.ikea.com" + bu
        elif bu and not bu.startswith("http://") and not bu.startswith("https://"):
            # Some sources store path-like strings (e.g. "eg/en/p/xxx/")
            bu = "https://www.ikea.com/" + bu.lstrip("/")
        out["buy_url"] = bu

    # Normalize in_stock field
    if "in_stock" in out:
        v = out.get("in_stock")
        if isinstance(v, bool):
            pass
        elif isinstance(v, (int, float)):
            out["in_stock"] = bool(v)
        elif isinstance(v, str):
            out["in_stock"] = v.strip().lower() in ("1", "true", "yes", "y", "in_stock")

    return out


@router.get("/products")
async def products_search(
    q:        str   = Query("",  description="Free-text search"),
    category: str   = Query("",  description="Furniture category (sofa, bed, desk…)"),
    budget:   float = Query(0,   description="Max price USD (0 = no limit)"),
    min_price: float = Query(0,  description="Min price USD"),
    in_stock: bool  = Query(True, description="In-stock only"),
    limit:    int   = Query(50,  description="Max results"),
    currency: str   = Query("",  description="Target currency (e.g. EGP). Uses env FX_<FROM>_TO_<TO> if needed."),
):
    """Search IKEA catalog with optional filters."""
    results = search_products(
        query=q,
        category=category,
        max_price=budget,
        min_price=min_price,
        in_stock=in_stock,
        limit=limit,
    )
    normalized = [_normalize_product(p) for p in (results or [])]
    if currency:
        tgt = currency.strip().upper()
        for p in normalized:
            src = (p.get("currency") or "USD").upper()
            # If the scraped price is USD but user wants EGP, use env FX_USD_TO_EGP.
            # If scraped is already EGP, this keeps it.
            price = p.get("price_usd")
            converted = _convert_money(price, src, tgt) if (price is not None) else None
            if converted is not None:
                p["price"] = converted
                p["currency"] = tgt
            else:
                # fall back to whatever we have
                p["price"] = p.get("price_usd") or p.get("price") or p.get("price_low")
    # Provide both keys for backward compatibility with existing frontend code
    return {"results": normalized, "products": normalized, "count": len(normalized), "query": q}


@router.get("/products/all")
async def get_all_products(
    limit: int = Query(200, ge=1, le=2000, description="Page size"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    q: str = Query("", description="Free-text search"),
    category: str = Query("", description="RoomState category (sofa, bed, desk, ...)"),
    in_stock: bool = Query(False, description="In-stock only"),
    currency: str = Query("", description="Target currency (e.g. EGP)"),
):
    """
    Paginated product listing for UI. Reads from SQLite when available (best for 'realtime scraping'),
    otherwise falls back to ikea_catalog.json.
    """
    # Prefer SQLite since it can grow during a running scrape job
    if SQLITE_DB.exists() and SQLITE_DB.stat().st_size > 1024:
        import sqlite3

        where = []
        params: list = []
        if q:
            where.append("(name LIKE ? OR series LIKE ? OR description LIKE ?)")
            qq = f"%{q}%"
            params += [qq, qq, qq]
        if category:
            where.append("(category = ? OR ikea_category = ?)")
            params += [category, category]
        if in_stock:
            where.append("in_stock = 1")

        where_sql = (" WHERE " + " AND ".join(where)) if where else ""

        con = sqlite3.connect(SQLITE_DB)
        con.row_factory = sqlite3.Row
        try:
            total = con.execute(f"SELECT COUNT(*) as n FROM products{where_sql}", params).fetchone()["n"]
            rows = con.execute(
                f"SELECT * FROM products{where_sql} ORDER BY scraped_at DESC LIMIT ? OFFSET ?",
                params + [limit, offset],
            ).fetchall()
        finally:
            con.close()

        products = [_normalize_product(dict(r)) for r in rows]
        if currency:
            tgt = currency.strip().upper()
            for p in products:
                src = (p.get("currency") or "USD").upper()
                price = p.get("price_usd")
                converted = _convert_money(price, src, tgt) if (price is not None) else None
                if converted is not None:
                    p["price"] = converted
                    p["currency"] = tgt
                else:
                    p["price"] = p.get("price_usd") or p.get("price") or p.get("price_low")

        return {"products": products, "count": len(products), "total": int(total), "limit": limit, "offset": offset}

    # JSON fallback
    import json
    if IKEA_JSON.exists():
        data = json.loads(IKEA_JSON.read_text(encoding="utf-8"))
        products = [_normalize_product(p) for p in (data.get("products", []) or [])]
        if q:
            qq = q.lower()
            products = [p for p in products if qq in " ".join([p.get("name",""), p.get("series",""), p.get("description","")]).lower()]
        if category:
            products = [p for p in products if (p.get("category") == category or p.get("ikea_category") == category)]
        if in_stock:
            products = [p for p in products if p.get("in_stock") is True]
        total = len(products)
        page = products[offset:offset + limit]
        return {"products": page, "count": len(page), "total": total, "limit": limit, "offset": offset}

    return {"products": [], "count": 0, "total": 0, "limit": limit, "offset": offset}


@router.get("/catalog/status")
async def catalog_status():
    """List active and recent scrape jobs (for 'realtime scraping' UI)."""
    # Return newest first
    jobs = sorted(_SCRAPE_JOBS.values(), key=lambda j: j.get("started_at", 0), reverse=True)
    return {"jobs": jobs[:20], "count": len(jobs)}


@router.get("/catalog/status/{job_id}")
async def catalog_status_one(job_id: str):
    job = _SCRAPE_JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return job


@router.post("/products/room")
async def products_for_room(room_state: dict):
    """
    Return IKEA product suggestions for every furniture piece currently in the room.
    Pass current RoomState as request body.
    """
    raw = get_products_for_room(room_state)

    # Normalize to the shape the frontend expects:
    # { suggestions: { [furniture_id]: { object_type, products: [...] } } }
    out: dict = {}
    for row in (raw or []):
        fid = row.get("furniture_id") or row.get("id") or row.get("object_id")
        if not fid:
            continue
        object_type = row.get("furniture_type") or row.get("object_type") or ""
        products = row.get("products") or row.get("suggestions") or []
        out[str(fid)] = {
            "object_type": object_type,
            "products": [_normalize_product(p) for p in (products or [])],
        }
    return {"suggestions": out}


@router.get("/products/substitute/{furniture_id}")
async def products_substitute(
    furniture_id: str,
    room_state:   dict,
    max_price:    float = Query(0),
    limit:        int   = Query(8),
):
    """
    Find IKEA products that fit the same spatial slot as the given furniture piece.
    Useful for the substitution engine: 'find me something that fits but costs less'.
    """
    alts = find_substitutes(furniture_id, room_state, max_price=max_price, limit=limit)
    if not alts:
        raise HTTPException(404, f"No substitutes found for {furniture_id}")
    return {"furniture_id": furniture_id, "alternatives": alts, "count": len(alts)}


@router.get("/products/{item_id}")
async def product_detail(item_id: str):
    """Get a single IKEA product by ID or article number."""
    product = get_product_by_id(item_id)
    if not product:
        raise HTTPException(404, f"Product {item_id} not found")
    return product


@router.get("/catalog/stats")
async def catalog_statistics():
    """Catalog health: total products, by-category breakdown, avg price."""
    return catalog_stats()


@router.post("/catalog/refresh")
async def catalog_refresh(
    categories: list[str] = Query(None, description="Categories to re-scrape (default: all)"),
    rate: float = Query(2.0, description="Requests per second"),
    cc: str = Query("us", description="IKEA country code (e.g. us, eg)"),
    lang: str = Query("en", description="IKEA language code (e.g. en, ar)"),
):
    """
    Trigger a background re-scrape of the IKEA catalog.
    Returns immediately — scrape runs as a background task.
    """
    from backend.scraper.ikea_scraper import IKEAScraper, DEPARTMENTS
    from backend.scraper.catalog_writer import save_ikea_json, save_sqlite, merge_into_project_catalog
    import httpx

    async with _SCRAPE_LOCK:
        job_id = uuid.uuid4().hex
        cats = categories or list(DEPARTMENTS.keys())
        job = {
            "job_id": job_id,
            "status": "running",
            "cc": cc,
            "lang": lang,
            "rate": rate,
            "categories": cats,
            "total_categories": len(cats),
            "done_categories": 0,
            "current_category": None,
            "products_total": 0,
            "started_at": time.time(),
            "finished_at": None,
            "error": None,
            "message": "Scrape started",
        }
        _SCRAPE_JOBS[job_id] = job

    async def _scrape_incremental(jid: str):
        job = _SCRAPE_JOBS.get(jid)
        if not job:
            return
        scraper = IKEAScraper(cc=cc, lang=lang, rate=rate)
        all_products = []
        seen = set()
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                for cat in cats:
                    job["current_category"] = cat
                    job["message"] = f"Scraping {cat}…"
                    batch = await scraper.scrape_category(client, cat, max_products=500)
                    new_count = 0
                    for p in batch:
                        if p.item_no and p.item_no not in seen:
                            seen.add(p.item_no)
                            all_products.append(p)
                            new_count += 1

                    # Persist incrementally so the UI can query /products/all while scraping
                    save_ikea_json(all_products)
                    save_sqlite(all_products)
                    merge_into_project_catalog(all_products)

                    job["done_categories"] += 1
                    job["products_total"] = len(all_products)
                    job["message"] = f"Scraped {cat}: +{new_count} (total {len(all_products)})"

            job["status"] = "finished"
            job["finished_at"] = time.time()
            job["current_category"] = None
            job["message"] = f"Scrape finished: {job['products_total']} products"
        except Exception as e:
            job["status"] = "error"
            job["finished_at"] = time.time()
            job["error"] = str(e)
            job["message"] = "Scrape failed"

    asyncio.create_task(_scrape_incremental(job_id))

    return {
        "status": "started",
        "job_id": job_id,
        "message": f"Scraping {len(cats)} categories in background (cc={cc}, lang={lang}). Use /catalog/status/{job_id} for progress.",
    }

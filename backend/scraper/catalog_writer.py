"""
IKEA Catalog Writer
===================
Saves scraped IKEAProduct objects into:
  - data/ikea_catalog.json          (full raw catalog, all fields)
  - data/furniture_catalog.json     (merged with existing project catalog)
  - data/ikea_catalog.db            (SQLite for fast lookup & filtering)

Run after ikea_scraper.py.
"""

import json
import logging
import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import os

from .ikea_scraper import IKEAProduct

log = logging.getLogger("catalog_writer")

DATA_DIR   = Path("data")
IKEA_JSON  = DATA_DIR / "ikea_catalog.json"
MERGED_JSON = DATA_DIR / "furniture_catalog.json"
SQLITE_DB  = DATA_DIR / "ikea_catalog.db"


# ─── JSON Writer ──────────────────────────────────────────────────────────────

def save_ikea_json(products: list[IKEAProduct]) -> Path:
    """Save full IKEA catalog as JSON."""
    DATA_DIR.mkdir(exist_ok=True)
    data = {
        "meta": {
            "total":      len(products),
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "source":     "ikea.com",
            "categories": sorted({p.ikea_category for p in products}),
        },
        "products": [asdict(p) for p in products],
    }
    # Atomic write to avoid partially-written JSON during live scraping / reload
    tmp = IKEA_JSON.with_suffix(IKEA_JSON.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, IKEA_JSON)
    log.info(f"Saved {len(products)} products → {IKEA_JSON}")
    return IKEA_JSON


# ─── Merged Catalog Writer ────────────────────────────────────────────────────

def _to_catalog_entry(p: IKEAProduct) -> dict:
    """
    Convert IKEAProduct to the project's furniture_catalog.json schema.
    Matches the shape used by product_search.py and the frontend.
    """
    return {
        # Core identity
        "id":          f"ikea_{p.item_no}",
        "name":        p.name,
        "series":      p.series,
        "description": p.description,
        "source":      "ikea",
        "item_no":     p.item_no,

        # Classification
        "category":    p.category,          # RoomState type ("sofa", "bed", etc.)
        "ikea_category": p.ikea_category,

        # 3D placement (meters)
        "size":   [p.width, p.depth],       # [width, depth] footprint
        "height": p.height,

        # Clearance for constraint solver
        "min_clearance": p.min_clearance,

        # Appearance
        "color":    p.color or "unknown",
        "colors":   p.colors,
        "color_variants": p.color_variants,  # [{id, name, image_url, price, pip_url}]
        "material": p.material,

        # Commerce — EGP prices for Egypt
        "price_low":  p.price_low  or p.price,
        "price_high": p.price_high or p.price,
        "price":      p.price,
        "currency":   p.currency,            # "EGP" for Egypt
        "in_stock":   p.in_stock,
        "buy_url":    p.buy_url,

        # Media — rich image gallery
        "image_url":          p.image_url,
        "image_urls":         p.image_urls,
        "image_urls_by_type": p.image_urls_by_type,  # {MAIN: [...], CONTEXT: [...], ...}

        # 3D / AR
        "model_url":  p.model_url,           # GLB URL for WebXR AR viewer

        # Physical
        "weight_kg": p.weight_kg,
    }


def merge_into_project_catalog(products: list[IKEAProduct]) -> Path:
    """
    Merge IKEA products into the project's existing furniture_catalog.json.
    Existing hand-crafted entries are preserved; IKEA entries are added/updated.
    """
    # Load existing catalog
    existing: dict[str, dict] = {}
    if MERGED_JSON.exists():
        try:
            raw = json.loads(MERGED_JSON.read_text())
            # Support both list and dict-of-list formats
            entries = raw if isinstance(raw, list) else raw.get("products", [])
            for e in entries:
                existing[e.get("id", "")] = e
        except Exception as e:
            log.warning(f"Could not parse existing catalog: {e}")

    # Add / update IKEA entries
    added   = 0
    updated = 0
    for p in products:
        entry = _to_catalog_entry(p)
        eid   = entry["id"]
        if eid in existing:
            existing[eid] = {**existing[eid], **entry}  # IKEA data wins
            updated += 1
        else:
            existing[eid] = entry
            added += 1

    # Write merged catalog
    all_entries = list(existing.values())
    # Atomic write to avoid empty/partial JSON on crash/reload
    tmp = MERGED_JSON.with_suffix(MERGED_JSON.suffix + ".tmp")
    tmp.write_text(json.dumps(all_entries, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, MERGED_JSON)
    log.info(f"Merged catalog: {added} added, {updated} updated → {MERGED_JSON} ({len(all_entries)} total)")
    return MERGED_JSON


# ─── SQLite Writer ────────────────────────────────────────────────────────────

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS products (
    id                    TEXT PRIMARY KEY,
    item_no               TEXT,
    name                  TEXT,
    series                TEXT,
    description           TEXT,
    category              TEXT,
    ikea_category         TEXT,
    width                 REAL,
    depth                 REAL,
    height                REAL,
    price                 REAL,
    price_low             REAL,
    price_high            REAL,
    currency              TEXT,
    color                 TEXT,
    material              TEXT,
    weight_kg             REAL,
    min_clearance         REAL,
    in_stock              INTEGER,
    image_url             TEXT,
    buy_url               TEXT,
    model_url             TEXT,
    colors_json           TEXT,
    image_urls_json       TEXT,
    image_urls_by_type_json TEXT,
    color_variants_json   TEXT,
    scraped_at            TEXT
);
CREATE INDEX IF NOT EXISTS idx_category     ON products(category);
CREATE INDEX IF NOT EXISTS idx_ikea_cat     ON products(ikea_category);
CREATE INDEX IF NOT EXISTS idx_price        ON products(price);
CREATE INDEX IF NOT EXISTS idx_name         ON products(name);
CREATE INDEX IF NOT EXISTS idx_series       ON products(series);
CREATE INDEX IF NOT EXISTS idx_in_stock     ON products(in_stock);
CREATE INDEX IF NOT EXISTS idx_model_url    ON products(model_url);
"""

def save_sqlite(products: list[IKEAProduct]) -> Path:
    """Save products to SQLite for fast querying."""
    DATA_DIR.mkdir(exist_ok=True)

    # Drop & recreate DB to apply schema changes cleanly
    con = sqlite3.connect(SQLITE_DB)
    cur = con.cursor()

    # Apply schema (CREATE IF NOT EXISTS + indexes)
    for stmt in CREATE_TABLE.strip().split(";"):
        stmt = stmt.strip()
        if stmt:
            try:
                cur.execute(stmt)
            except sqlite3.OperationalError:
                pass  # Index already exists etc.

    # Try to add new columns to existing tables (migration)
    new_cols = [
        ("model_url",               "TEXT"),
        ("image_urls_by_type_json",  "TEXT"),
        ("color_variants_json",      "TEXT"),
    ]
    for col_name, col_type in new_cols:
        try:
            cur.execute(f"ALTER TABLE products ADD COLUMN {col_name} {col_type}")
        except sqlite3.OperationalError:
            pass  # Column already exists

    rows = [
        (
            f"ikea_{p.item_no}",
            p.item_no,
            p.name,
            p.series,
            p.description,
            p.category,
            p.ikea_category,
            p.width,
            p.depth,
            p.height,
            p.price,
            p.price_low,
            p.price_high,
            p.currency,
            p.color,
            p.material,
            p.weight_kg,
            p.min_clearance,
            int(p.in_stock),
            p.image_url,
            p.buy_url,
            p.model_url,
            json.dumps(p.colors,              ensure_ascii=False),
            json.dumps(p.image_urls,          ensure_ascii=False),
            json.dumps(p.image_urls_by_type,  ensure_ascii=False),
            json.dumps(p.color_variants,      ensure_ascii=False),
            p.scraped_at,
        )
        for p in products
        if p.item_no
    ]

    cur.executemany(
        """INSERT OR REPLACE INTO products VALUES
           (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        rows,
    )
    con.commit()
    con.close()

    log.info(f"Saved {len(rows)} products → {SQLITE_DB}")
    return SQLITE_DB


# ─── Query Helper (used by product_search.py) ─────────────────────────────────

class IKEACatalogDB:
    """
    Fast local IKEA catalog queries backed by SQLite.
    Plug this into backend/catalog/product_search.py.
    """

    def __init__(self, db_path: Path = SQLITE_DB):
        self.db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        return con

    def search(
        self,
        query:    str  = "",
        category: str  = "",
        max_price: float = 0,
        min_price: float = 0,
        in_stock:  bool  = False,
        limit:     int   = 20,
    ) -> list[dict]:
        """Full-text + filter search across catalog."""
        where  = []
        params = []

        if query:
            where.append("(name LIKE ? OR series LIKE ? OR description LIKE ?)")
            q = f"%{query}%"
            params += [q, q, q]

        if category:
            where.append("(category = ? OR ikea_category = ?)")
            params += [category, category]

        if max_price > 0:
            where.append("price <= ?")
            params.append(max_price)

        if min_price > 0:
            where.append("price >= ?")
            params.append(min_price)

        if in_stock:
            where.append("in_stock = 1")

        sql = "SELECT * FROM products"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY price ASC LIMIT ?"
        params.append(limit)

        with self._conn() as con:
            rows = con.execute(sql, params).fetchall()

        return [self._row_to_dict(r) for r in rows]

    def get_by_id(self, item_id: str) -> dict | None:
        """Fetch one product by id or item_no."""
        with self._conn() as con:
            row = con.execute(
                "SELECT * FROM products WHERE id = ? OR item_no = ?",
                (item_id, item_id)
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def get_by_category(self, category: str, limit: int = 50) -> list[dict]:
        """Get all products in a furniture category."""
        with self._conn() as con:
            rows = con.execute(
                "SELECT * FROM products WHERE category = ? ORDER BY price ASC LIMIT ?",
                (category, limit)
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def find_alternatives(
        self,
        category:  str,
        max_width: float,
        max_depth: float,
        max_price: float = 0,
        limit:     int   = 10,
    ) -> list[dict]:
        """
        Find products in the same category that fit within spatial constraints.
        Used by the substitution engine when a piece doesn't fit in the room.
        """
        params = [category, max_width, max_depth]
        price_clause = ""
        if max_price > 0:
            price_clause = "AND price <= ?"
            params.append(max_price)

        sql = f"""
            SELECT * FROM products
            WHERE category = ?
              AND width  <= ?
              AND depth  <= ?
              {price_clause}
            ORDER BY price ASC
            LIMIT ?
        """
        params.append(limit)

        with self._conn() as con:
            rows = con.execute(sql, params).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def catalog_stats(self) -> dict:
        """Summary stats for health check / admin."""
        with self._conn() as con:
            total     = con.execute("SELECT COUNT(*) FROM products").fetchone()[0]
            by_cat    = con.execute(
                "SELECT category, COUNT(*) as n FROM products GROUP BY category ORDER BY n DESC"
            ).fetchall()
            price_avg = con.execute("SELECT AVG(price) FROM products WHERE price > 0").fetchone()[0]
            in_stock  = con.execute("SELECT COUNT(*) FROM products WHERE in_stock = 1").fetchone()[0]
            has_model = con.execute("SELECT COUNT(*) FROM products WHERE model_url != ''").fetchone()[0]
            currency  = con.execute("SELECT currency FROM products LIMIT 1").fetchone()
            currency  = currency[0] if currency else "EGP"

        return {
            "total":            total,
            "in_stock":         in_stock,
            "has_3d_model":     has_model,
            "avg_price":        round(price_avg or 0, 2),
            "currency":         currency,
            "by_category":      {r[0]: r[1] for r in by_cat},
        }

    @staticmethod
    def _row_to_dict(row) -> dict:
        if row is None:
            return {}
        d = dict(row)

        def _safe_json(val, default):
            if not val:
                return default
            try:
                return json.loads(val)
            except (json.JSONDecodeError, TypeError, ValueError):
                return default

        d["colors"]             = _safe_json(d.get("colors_json"),             [])
        d["image_urls"]         = _safe_json(d.get("image_urls_json"),         [])
        d["image_urls_by_type"] = _safe_json(d.get("image_urls_by_type_json"), {})
        d["color_variants"]     = _safe_json(d.get("color_variants_json"),     [])
        d.pop("colors_json",             None)
        d.pop("image_urls_json",         None)
        d.pop("image_urls_by_type_json", None)
        d.pop("color_variants_json",     None)
        return d

"""
Compatibility migrations for legacy flat data files -> tenant-scoped records.
"""

from __future__ import annotations

import json
from pathlib import Path


DATA_DIR = Path("data")


def migrate_comments_default_tenant():
    p = DATA_DIR / "comments.json"
    if not p.exists():
        return {"migrated": 0}
    try:
        rows = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"migrated": 0}
    if not isinstance(rows, list):
        return {"migrated": 0}
    n = 0
    for r in rows:
        if isinstance(r, dict) and "tenant_id" not in r:
            r["tenant_id"] = "default"
            n += 1
    if n:
        p.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"migrated": n}


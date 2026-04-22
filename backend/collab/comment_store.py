"""
Phase 5.5 — Comment pins (MVP)
File-backed comment pins for the current project/room.
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path


DATA_DIR = Path("data")
COMMENTS_PATH = DATA_DIR / "comments.json"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def list_comments(tenant_id: str = "default") -> list[dict]:
    if not COMMENTS_PATH.exists():
        return []
    try:
        data = json.loads(COMMENTS_PATH.read_text(encoding="utf-8"))
        rows = data if isinstance(data, list) else []
        return [r for r in rows if (r.get("tenant_id") or "default") == (tenant_id or "default")]
    except Exception:
        return []


def add_comment(text: str, x: float, y: float, z: float, object_id: str = "", tenant_id: str = "default") -> dict:
    row = {
        "id": uuid.uuid4().hex,
        "tenant_id": tenant_id or "default",
        "text": text,
        "object_id": object_id,
        "pos": {"x": float(x), "y": float(y), "z": float(z)},
        "created_at": time.time(),
    }
    # keep all-tenant rows in one file, filter on reads
    items = []
    if COMMENTS_PATH.exists():
        try:
            data = json.loads(COMMENTS_PATH.read_text(encoding="utf-8"))
            if isinstance(data, list):
                items = data
        except Exception:
            items = []
    items.append(row)
    COMMENTS_PATH.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
    return row


def update_comment(comment_id: str, text: str, tenant_id: str = "default") -> dict | None:
    if not COMMENTS_PATH.exists():
        return None
    try:
        rows = json.loads(COMMENTS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(rows, list):
        return None
    updated = None
    for r in rows:
        if isinstance(r, dict) and r.get("id") == comment_id and (r.get("tenant_id") or "default") == (tenant_id or "default"):
            r["text"] = text
            updated = r
            break
    if updated is not None:
        COMMENTS_PATH.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    return updated


def delete_comment(comment_id: str, tenant_id: str = "default") -> bool:
    if not COMMENTS_PATH.exists():
        return False
    try:
        rows = json.loads(COMMENTS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return False
    if not isinstance(rows, list):
        return False
    out = [r for r in rows if not (isinstance(r, dict) and r.get("id") == comment_id and (r.get("tenant_id") or "default") == (tenant_id or "default"))]
    if len(out) == len(rows):
        return False
    COMMENTS_PATH.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    return True


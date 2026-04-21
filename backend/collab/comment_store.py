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


def list_comments() -> list[dict]:
    if not COMMENTS_PATH.exists():
        return []
    try:
        data = json.loads(COMMENTS_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def add_comment(text: str, x: float, y: float, z: float, object_id: str = "") -> dict:
    row = {
        "id": uuid.uuid4().hex,
        "text": text,
        "object_id": object_id,
        "pos": {"x": float(x), "y": float(y), "z": float(z)},
        "created_at": time.time(),
    }
    items = list_comments()
    items.append(row)
    COMMENTS_PATH.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
    return row


"""
Phase 5.5 — Share links (MVP)
File-backed share tokens that snapshot current RoomState dict.
"""

from __future__ import annotations

import json
import secrets
import time
from pathlib import Path


DATA_DIR = Path("data")
SHARE_DIR = DATA_DIR / "shared"
SHARE_DIR.mkdir(parents=True, exist_ok=True)


def _share_path(token: str) -> Path:
    safe = "".join(c for c in token if c.isalnum())[:64]
    return SHARE_DIR / f"{safe}.json"


def create_share(room_state: dict, role: str = "view") -> dict:
    token = secrets.token_urlsafe(16)
    payload = {
        "token": token,
        "role": role if role in ("view", "edit") else "view",
        "created_at": time.time(),
        "room_state": room_state,
    }
    _share_path(token).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"token": token, "role": payload["role"]}


def load_share(token: str) -> dict | None:
    p = _share_path(token)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


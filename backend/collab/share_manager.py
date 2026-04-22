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


def _share_path(token: str, tenant_id: str = "default") -> Path:
    safe = "".join(c for c in token if c.isalnum())[:64]
    t = "".join(c for c in (tenant_id or "default") if c.isalnum() or c in ("-", "_"))[:64] or "default"
    return SHARE_DIR / f"{t}_{safe}.json"


def create_share(room_state: dict, role: str = "view", tenant_id: str = "default", ttl_seconds: int = 7 * 24 * 3600) -> dict:
    token = secrets.token_urlsafe(16)
    payload = {
        "token": token,
        "tenant_id": tenant_id,
        "role": role if role in ("view", "edit") else "view",
        "created_at": time.time(),
        "expires_at": time.time() + max(3600, int(ttl_seconds)),
        "room_state": room_state,
    }
    _share_path(token, tenant_id=tenant_id).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"token": token, "role": payload["role"]}


def load_share(token: str, tenant_id: str = "default") -> dict | None:
    p = _share_path(token, tenant_id=tenant_id)
    if not p.exists():
        return None
    try:
        row = json.loads(p.read_text(encoding="utf-8"))
        if time.time() > float(row.get("expires_at", 0)):
            return None
        return row
    except Exception:
        return None


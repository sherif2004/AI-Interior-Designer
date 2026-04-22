"""
Phase 5.6 — Home project store (MVP)
File-backed storage for a single HomeState (can be extended to multiple homes).
"""

from __future__ import annotations

import json
from pathlib import Path


DATA_DIR = Path("data")
DATA_DIR.mkdir(parents=True, exist_ok=True)


def _home_path(tenant_id: str = "default") -> Path:
    t = "".join(c for c in (tenant_id or "default") if c.isalnum() or c in ("-", "_"))[:64] or "default"
    return DATA_DIR / f"home_{t}.json"


def load_home(tenant_id: str = "default") -> dict:
    HOME_PATH = _home_path(tenant_id)
    if not HOME_PATH.exists():
        return {"id": "default_home", "name": "My Home", "rooms": {}, "connections": []}
    try:
        return json.loads(HOME_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"id": "default_home", "name": "My Home", "rooms": {}, "connections": []}


def save_home(home: dict, tenant_id: str = "default") -> dict:
    HOME_PATH = _home_path(tenant_id)
    HOME_PATH.write_text(json.dumps(home, indent=2, ensure_ascii=False), encoding="utf-8")
    return home


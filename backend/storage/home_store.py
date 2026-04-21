"""
Phase 5.6 — Home project store (MVP)
File-backed storage for a single HomeState (can be extended to multiple homes).
"""

from __future__ import annotations

import json
from pathlib import Path


DATA_DIR = Path("data")
HOME_PATH = DATA_DIR / "home.json"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_home() -> dict:
    if not HOME_PATH.exists():
        return {"id": "default_home", "name": "My Home", "rooms": {}, "connections": []}
    try:
        return json.loads(HOME_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"id": "default_home", "name": "My Home", "rooms": {}, "connections": []}


def save_home(home: dict) -> dict:
    HOME_PATH.write_text(json.dumps(home, indent=2, ensure_ascii=False), encoding="utf-8")
    return home


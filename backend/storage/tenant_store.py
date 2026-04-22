"""
Phase 6.0 — Multi-site tenant config store (MVP)
-------------------------------------------------
File-backed tenant configs resolved by host/subdomain.
"""

from __future__ import annotations

import json
from pathlib import Path


DATA_DIR = Path("data")
TENANTS_PATH = DATA_DIR / "tenants.json"
DATA_DIR.mkdir(parents=True, exist_ok=True)


DEFAULT_TENANT = {
    "id": "default",
    "name": "Planner 5D AI",
    "domains": ["localhost", "127.0.0.1"],
    "branding": {
        "app_title": "Planner 5D AI",
        "meta_description": "Professional SaaS AI Home Planner",
    },
    "feature_flags": {
        "catalog": True,
        "commerce": True,
        "versions": True,
        "blueprint": True,
        "scan": True,
        "voice": True,
        "sketch": True,
        "collab": True,
        "home": True,
        "ar": True,
    },
    "services": [
        {"id": "floorplan", "label": "2D/3D Floor Planning", "enabled": True},
        {"id": "ai_render", "label": "AI 4K Rendering", "enabled": True},
        {"id": "ar_preview", "label": "AR Product Preview", "enabled": True},
        {"id": "commerce", "label": "Shopping & Budget", "enabled": True},
        {"id": "collab", "label": "Share & Comments", "enabled": True},
    ],
}


def _bootstrap() -> dict:
    if TENANTS_PATH.exists():
        try:
            raw = json.loads(TENANTS_PATH.read_text(encoding="utf-8"))
            if isinstance(raw, dict) and isinstance(raw.get("tenants"), list):
                return raw
        except Exception:
            pass
    payload = {"tenants": [DEFAULT_TENANT]}
    TENANTS_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload


def list_tenants() -> list[dict]:
    return _bootstrap().get("tenants", [])


def resolve_tenant(host: str) -> dict:
    host = (host or "").split(":")[0].strip().lower()
    tenants = list_tenants()
    # exact domain match
    for t in tenants:
        for d in (t.get("domains") or []):
            if host == str(d).lower():
                return t
    # fallback: subdomain to tenant id, e.g. acme.localhost
    parts = host.split(".")
    if len(parts) >= 2:
        sub = parts[0]
        for t in tenants:
            if t.get("id") == sub:
                return t
    return tenants[0] if tenants else DEFAULT_TENANT


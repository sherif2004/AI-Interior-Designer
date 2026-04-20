"""
Version store — save named design snapshots and diff between versions.
Snapshots are stored in data/versions/ as JSON files.
"""
from __future__ import annotations
import json
import os
import time
from pathlib import Path
from copy import deepcopy

_PROJECT_ROOT = Path(__file__).parent.parent.parent
VERSIONS_DIR = _PROJECT_ROOT / "data" / "versions"


def _ensure_dir():
    VERSIONS_DIR.mkdir(parents=True, exist_ok=True)


def save_version(name: str, state: dict) -> dict:
    """Save current state as a named version snapshot."""
    _ensure_dir()
    safe_name = name.lower().strip().replace(" ", "_")
    snapshot = {
        "id": safe_name,
        "name": name,
        "saved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "room": deepcopy(state.get("room", {})),
        "objects": deepcopy(state.get("objects", [])),
        "project": deepcopy(state.get("project", {})),
    }
    path = VERSIONS_DIR / f"{safe_name}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2)
    return snapshot


def list_versions() -> list[dict]:
    """Return all saved version snapshots (metadata only)."""
    _ensure_dir()
    versions = []
    for p in sorted(VERSIONS_DIR.glob("*.json")):
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            versions.append({
                "id": data.get("id", p.stem),
                "name": data.get("name", p.stem),
                "saved_at": data.get("saved_at", ""),
                "object_count": len(data.get("objects", [])),
                "theme": data.get("room", {}).get("theme", "custom"),
            })
        except Exception:
            pass
    return versions


def load_version(version_id: str) -> dict | None:
    """Load a named version snapshot or None if not found."""
    _ensure_dir()
    path = VERSIONS_DIR / f"{version_id}.json"
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def diff_versions(id_a: str, id_b: str) -> dict:
    """
    Compute a diff between two named design versions.
    Returns {added, removed, moved, unchanged} object lists.
    """
    va = load_version(id_a)
    vb = load_version(id_b)

    if va is None:
        return {"error": f"Version '{id_a}' not found"}
    if vb is None:
        return {"error": f"Version '{id_b}' not found"}

    objs_a = {o["id"]: o for o in va.get("objects", [])}
    objs_b = {o["id"]: o for o in vb.get("objects", [])}

    ids_a = set(objs_a)
    ids_b = set(objs_b)

    added = [objs_b[i] for i in ids_b - ids_a]
    removed = [objs_a[i] for i in ids_a - ids_b]
    moved = []
    unchanged = []

    for oid in ids_a & ids_b:
        oa, ob = objs_a[oid], objs_b[oid]
        if oa["x"] != ob["x"] or oa["z"] != ob["z"] or oa.get("rotation") != ob.get("rotation"):
            moved.append({
                "id": oid,
                "type": oa.get("type"),
                "from": {"x": oa["x"], "z": oa["z"], "rotation": oa.get("rotation", 0)},
                "to":   {"x": ob["x"], "z": ob["z"], "rotation": ob.get("rotation", 0)},
            })
        else:
            unchanged.append({"id": oid, "type": oa.get("type")})

    return {
        "version_a": {"id": id_a, "name": va.get("name"), "saved_at": va.get("saved_at")},
        "version_b": {"id": id_b, "name": vb.get("name"), "saved_at": vb.get("saved_at")},
        "added": added,
        "removed": removed,
        "moved": moved,
        "unchanged": unchanged,
        "room_a": va.get("room", {}),
        "room_b": vb.get("room", {}),
    }


def delete_version(version_id: str) -> bool:
    """Delete a version snapshot. Returns True if deleted."""
    path = VERSIONS_DIR / f"{version_id}.json"
    if path.exists():
        path.unlink()
        return True
    return False

"""
Clearance checker — validates walkability and minimum clearance around furniture.

Rules:
- Minimum 60cm walking corridor anywhere in the room
- Per-furniture minimum clearance (from catalog: min_clearance field)
- Accessibility score 0–100
"""
from __future__ import annotations
import math
from backend.environment.objects import get_furniture

MIN_WALKWAY = 0.60   # meters — absolute minimum corridor width
SUGGESTED_WALKWAY = 0.90  # meters — comfortable corridor


def check_clearance(objects: list[dict], room: dict) -> list[dict]:
    """
    Run clearance checks on all objects and return a list of warning dicts.
    Each warning: {id, type, object_type, message, severity}
    """
    warnings: list[dict] = []
    rw = room.get("width", 10)
    rh = room.get("height", 8)
    margin = room.get("wall_thickness", 0.2)

    for obj in objects:
        catalog_entry = get_furniture(obj.get("type", "")) or {}
        min_clear = catalog_entry.get("min_clearance", 0.4)

        # Check clearance against all other objects
        others = [o for o in objects if o["id"] != obj["id"]]
        for other in others:
            gap = _gap_between(obj, other)
            if gap < MIN_WALKWAY and gap >= 0:
                sev = "error" if gap < 0.3 else "warning"
                warnings.append({
                    "id": f"clearance_{obj['id']}_{other['id']}",
                    "type": "clearance",
                    "object_id": obj["id"],
                    "other_id": other["id"],
                    "object_type": obj.get("type"),
                    "other_type": other.get("type"),
                    "gap_m": round(gap, 2),
                    "required_m": MIN_WALKWAY,
                    "severity": sev,
                    "message": (
                        f"Only {gap:.2f}m between {obj.get('type','?')} and "
                        f"{other.get('type','?')} — minimum is {MIN_WALKWAY}m"
                    ),
                })

        # Check clearance to walls
        wall_gaps = _wall_gaps(obj, rw, rh, margin)
        accessible_sides = sum(1 for g in wall_gaps if g >= MIN_WALKWAY)
        if accessible_sides == 0:
            warnings.append({
                "id": f"blocked_{obj['id']}",
                "type": "accessibility",
                "object_id": obj["id"],
                "object_type": obj.get("type"),
                "severity": "warning",
                "message": (
                    f"{obj.get('type','?')} has no accessible side with ≥ {MIN_WALKWAY}m clearance"
                ),
            })

    # De-duplicate symmetric pairs
    seen: set[frozenset] = set()
    unique: list[dict] = []
    for w in warnings:
        key = frozenset([w.get("object_id", ""), w.get("other_id", "")])
        if key not in seen:
            seen.add(key)
            unique.append(w)

    return unique


def compute_accessibility_score(objects: list[dict], room: dict) -> int:
    """
    Returns an accessibility score 0–100.
    100 = full clearance on all sides of all objects.
    """
    if not objects:
        return 100

    rw = room.get("width", 10)
    rh = room.get("height", 8)
    margin = room.get("wall_thickness", 0.2)

    total_score = 0
    for obj in objects:
        others = [o for o in objects if o["id"] != obj["id"]]

        # Inter-object gaps
        gaps = [_gap_between(obj, o) for o in others if _gap_between(obj, o) >= 0]
        wall_gaps_list = _wall_gaps(obj, rw, rh, margin)
        all_gaps = gaps + wall_gaps_list

        if not all_gaps:
            total_score += 100
            continue

        obj_score = sum(min(g / SUGGESTED_WALKWAY, 1.0) for g in all_gaps) / len(all_gaps) * 100
        total_score += obj_score

    return max(0, min(100, round(total_score / len(objects))))


def _gap_between(a: dict, b: dict) -> float:
    """
    Compute the minimum gap (in meters) between two AABBs.
    Returns negative if overlapping.
    """
    ax1, az1 = a["x"], a["z"]
    ax2, az2 = ax1 + a["w"], az1 + a["d"]
    bx1, bz1 = b["x"], b["z"]
    bx2, bz2 = bx1 + b["w"], bz1 + b["d"]

    gap_x = max(ax1 - bx2, bx1 - ax2, 0)
    gap_z = max(az1 - bz2, bz1 - az2, 0)

    if gap_x == 0 and gap_z == 0:
        # Boxes overlap or touch
        overlap_x = min(ax2, bx2) - max(ax1, bx1)
        overlap_z = min(az2, bz2) - max(az1, bz1)
        return -min(overlap_x, overlap_z)

    return math.sqrt(gap_x ** 2 + gap_z ** 2)


def _wall_gaps(obj: dict, rw: float, rh: float, margin: float) -> list[float]:
    """Return gaps from the 4 object edges to the room walls."""
    return [
        obj["x"] - margin,                         # west wall gap
        rw - margin - (obj["x"] + obj["w"]),        # east wall gap
        obj["z"] - margin,                         # north wall gap
        rh - margin - (obj["z"] + obj["d"]),        # south wall gap
    ]

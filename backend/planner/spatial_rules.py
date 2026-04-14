"""
Spatial reasoning engine — maps symbolic placement rules to (x, z) coordinates.
"""
import math
from typing import Optional


DIRECTION_DELTAS = {
    "left":     (-1.0, 0.0),
    "right":    (1.0,  0.0),
    "up":       (0.0, -1.0),
    "forward":  (0.0, -1.0),
    "down":     (0.0,  1.0),
    "backward": (0.0,  1.0),
    "north":    (0.0, -1.0),
    "south":    (0.0,  1.0),
    "east":     (1.0,  0.0),
    "west":     (-1.0, 0.0),
}


def resolve_placement(
    placement: str,
    room: dict,
    objects: list[dict],
    obj_w: float,
    obj_d: float,
    reference_id: Optional[str] = None,
) -> tuple[float, float]:
    """
    Resolve a symbolic placement string to (x, z) coordinates.
    Returns best-guess position; constraint solver will validate/nudge.
    """
    rw = room["width"]
    rh = room["height"]
    margin = room.get("wall_thickness", 0.2) + 0.1

    placement = placement.lower().strip()

    # ---- CORNER placements ----
    if placement == "corner":
        return _best_corner(rw, rh, obj_w, obj_d, objects, margin)

    if placement == "corner_nw":
        return (margin, margin)
    if placement == "corner_ne":
        return (rw - margin - obj_w, margin)
    if placement == "corner_sw":
        return (margin, rh - margin - obj_d)
    if placement == "corner_se":
        return (rw - margin - obj_w, rh - margin - obj_d)

    # ---- CENTER ----
    if placement in ("center", "middle"):
        return (rw / 2 - obj_w / 2, rh / 2 - obj_d / 2)

    # ---- AGAINST WALL ----
    if placement == "against_wall_north" or placement == "near_wall_north":
        return (_center_x(rw, obj_w), margin)
    if placement == "against_wall_south" or placement == "near_wall_south":
        return (_center_x(rw, obj_w), rh - margin - obj_d)
    if placement == "against_wall_east" or placement == "near_wall_east":
        return (rw - margin - obj_w, _center_z(rh, obj_d))
    if placement == "against_wall_west" or placement == "near_wall_west":
        return (margin, _center_z(rh, obj_d))

    if placement in ("near_wall", "against_wall"):
        return _best_wall(rw, rh, obj_w, obj_d, objects, margin)

    # ---- RELATIVE: next_to:<id> ----
    if placement.startswith("next_to:") or placement.startswith("next_to_"):
        ref_id = placement.split(":", 1)[-1].replace("_", " ")
        ref = _find_object(objects, reference_id or ref_id)
        if ref:
            return _adjacent_position(ref, obj_w, obj_d, rw, rh, margin)

    # ---- RELATIVE: in_front_of:<id> ----
    if placement.startswith("in_front_of:") or placement.startswith("in_front_of_"):
        ref_id = placement.split(":", 1)[-1].replace("_", " ")
        ref = _find_object(objects, reference_id or ref_id)
        if ref:
            return _in_front_of(ref, obj_w, obj_d, rw, rh, margin)

    # ---- AUTO / FALLBACK ----
    return _auto_place(rw, rh, obj_w, obj_d, objects, margin)


# ─────────────────────────────── helpers ────────────────────────────────────

def _center_x(rw: float, obj_w: float) -> float:
    return rw / 2 - obj_w / 2


def _center_z(rh: float, obj_d: float) -> float:
    return rh / 2 - obj_d / 2


def _find_object(objects: list[dict], ref: str) -> Optional[dict]:
    """Find object by ID or type (returns first match)."""
    ref = ref.lower().strip()
    for obj in objects:
        if obj["id"].lower() == ref or obj["type"].lower() == ref:
            return obj
    # partial match
    for obj in objects:
        if ref in obj["id"].lower() or ref in obj["type"].lower():
            return obj
    return None


def _best_corner(rw, rh, w, d, objects, margin) -> tuple[float, float]:
    corners = [
        (margin, margin),
        (rw - margin - w, margin),
        (margin, rh - margin - d),
        (rw - margin - w, rh - margin - d),
    ]
    # Pick corner with fewest nearby objects
    best = corners[0]
    best_count = float("inf")
    for cx, cz in corners:
        count = sum(
            1 for o in objects
            if abs(o["x"] - cx) < 2.0 and abs(o["z"] - cz) < 2.0
        )
        if count < best_count:
            best_count = count
            best = (cx, cz)
    return best


def _best_wall(rw, rh, w, d, objects, margin) -> tuple[float, float]:
    candidates = [
        (_center_x(rw, w), margin),                  # north
        (_center_x(rw, w), rh - margin - d),          # south
        (margin, _center_z(rh, d)),                   # west
        (rw - margin - w, _center_z(rh, d)),          # east
    ]
    return _least_crowded(candidates, objects)


def _least_crowded(candidates: list, objects: list) -> tuple[float, float]:
    best = candidates[0]
    best_count = float("inf")
    for cx, cz in candidates:
        count = sum(
            1 for o in objects
            if abs(o["x"] - cx) < 1.5 and abs(o["z"] - cz) < 1.5
        )
        if count < best_count:
            best_count = count
            best = (cx, cz)
    return best


def _adjacent_position(ref: dict, w: float, d: float, rw: float, rh: float, margin: float) -> tuple[float, float]:
    gap = 0.1
    candidates = [
        (ref["x"] + ref["w"] + gap, ref["z"]),     # right of ref
        (ref["x"] - w - gap, ref["z"]),              # left of ref
        (ref["x"], ref["z"] + ref["d"] + gap),       # below ref
        (ref["x"], ref["z"] - d - gap),              # above ref
    ]
    for cx, cz in candidates:
        if margin <= cx and cx + w <= rw - margin:
            if margin <= cz and cz + d <= rh - margin:
                return (cx, cz)
    return (ref["x"] + ref["w"] + gap, ref["z"])


def _in_front_of(ref: dict, w: float, d: float, rw: float, rh: float, margin: float) -> tuple[float, float]:
    rot = ref.get("rotation", 0)
    gap = 0.5
    if rot == 0:   # facing south
        x = ref["x"] + ref["w"] / 2 - w / 2
        z = ref["z"] + ref["d"] + gap
    elif rot == 90:  # facing east
        x = ref["x"] + ref["w"] + gap
        z = ref["z"] + ref["d"] / 2 - d / 2
    elif rot == 180:  # facing north
        x = ref["x"] + ref["w"] / 2 - w / 2
        z = ref["z"] - d - gap
    else:  # facing west
        x = ref["x"] - w - gap
        z = ref["z"] + ref["d"] / 2 - d / 2

    x = max(margin, min(x, rw - margin - w))
    z = max(margin, min(z, rh - margin - d))
    return (x, z)


def _auto_place(rw, rh, w, d, objects, margin) -> tuple[float, float]:
    """Grid-scan to find first available spot (left-to-right, top-to-bottom)."""
    step = 0.5
    z = margin
    while z + d <= rh - margin:
        x = margin
        while x + w <= rw - margin:
            if _is_free(x, z, w, d, objects):
                return (x, z)
            x += step
        z += step
    # Fallback: center
    return (rw / 2 - w / 2, rh / 2 - d / 2)


def _is_free(x: float, z: float, w: float, d: float, objects: list) -> bool:
    for obj in objects:
        if _aabb_overlap(x, z, w, d, obj["x"], obj["z"], obj["w"], obj["d"]):
            return False
    return True


def _aabb_overlap(ax, az, aw, ad, bx, bz, bw, bd, gap=0.1) -> bool:
    return not (
        ax + aw + gap <= bx
        or bx + bw + gap <= ax
        or az + ad + gap <= bz
        or bz + bd + gap <= az
    )


def apply_direction(obj: dict, direction: str, amount: float, room: dict) -> tuple[float, float]:
    """Apply a directional move to an object, returning new (x, z) clamped to room."""
    dx, dz = DIRECTION_DELTAS.get(direction, (0, 0))
    margin = room.get("wall_thickness", 0.2) + 0.1
    new_x = obj["x"] + dx * amount
    new_z = obj["z"] + dz * amount
    # Clamp
    new_x = max(margin, min(new_x, room["width"] - margin - obj["w"]))
    new_z = max(margin, min(new_z, room["height"] - margin - obj["d"]))
    return (new_x, new_z)

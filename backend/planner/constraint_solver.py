"""
Constraint solver — validates placement and auto-nudges if needed.
"""
from backend.planner.spatial_rules import _aabb_overlap, _is_free


MAX_NUDGE_ATTEMPTS = 24
NUDGE_STEP = 0.3


def solve(
    x: float,
    z: float,
    w: float,
    d: float,
    room: dict,
    existing_objects: list[dict],
    exclude_id: str = None,
) -> tuple[float, float, str | None]:
    """
    Attempt to place an object at (x, z) with size (w, d).
    Returns (final_x, final_z, error_message).
    error_message is None on success.
    """
    margin = room.get("wall_thickness", 0.2) + 0.05
    rw = room["width"]
    rh = room["height"]

    others = [o for o in existing_objects if o.get("id") != exclude_id]

    # Clamp to room first
    x = max(margin, min(x, rw - margin - w))
    z = max(margin, min(z, rh - margin - d))

    if _is_free_with_margin(x, z, w, d, others):
        return (x, z, None)

    # Try nudging in concentric rings
    for attempt in range(1, MAX_NUDGE_ATTEMPTS + 1):
        step = attempt * NUDGE_STEP
        candidates = _ring_candidates(x, z, step)
        for cx, cz in candidates:
            cx = max(margin, min(cx, rw - margin - w))
            cz = max(margin, min(cz, rh - margin - d))
            if _is_free_with_margin(cx, cz, w, d, others):
                return (cx, cz, None)

    return (x, z, f"Could not place {w}×{d} object without collision after {MAX_NUDGE_ATTEMPTS} attempts")


def _is_free_with_margin(x, z, w, d, objects, gap=0.1) -> bool:
    for obj in objects:
        if _aabb_overlap(x, z, w, d, obj["x"], obj["z"], obj["w"], obj["d"], gap):
            return False
    return True


def _ring_candidates(cx: float, cz: float, step: float) -> list[tuple[float, float]]:
    """Generate 8 directional candidate positions at 'step' distance."""
    return [
        (cx + step, cz),
        (cx - step, cz),
        (cx,        cz + step),
        (cx,        cz - step),
        (cx + step, cz + step),
        (cx - step, cz + step),
        (cx + step, cz - step),
        (cx - step, cz - step),
    ]

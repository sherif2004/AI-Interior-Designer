"""
Layout Scorer — Phase 4B
========================
5-dimension layout quality scoring system.
Evaluates a RoomState and returns an overall 0–100 score
plus per-dimension breakdowns with actionable improvement notes.

Dimensions:
  1. Walkability       (25%) — 60cm+ clear paths throughout
  2. Functional Zoning (25%) — furniture purpose zones respected
  3. Visual Balance    (20%) — symmetry, focal points, alignment
  4. Object Relations  (20%) — sofa↔TV, bed↔walls, desk↔window
  5. Natural Light     (10%) — furniture not blocking windows
"""

from __future__ import annotations
import math
from typing import Any

# ─── Constants ────────────────────────────────────────────────────────────────

MIN_WALKWAY_M  = 0.60   # ANSI/HFS minimum aisle width
IDEAL_WALKWAY  = 0.90   # comfortable, scores highest
TV_SOFA_IDEAL  = (2.0, 3.5)   # ideal TV-to-sofa distance range (m)
DESK_WINDOW_MAX = 2.0   # desk should be within 2m of a window
BED_WALL_MAX   = 0.30   # bed should be ≤30cm from at least one wall

BEDROOM_TYPES  = {"bed", "single_bed", "nightstand", "wardrobe", "dresser"}
LIVING_TYPES   = {"sofa", "armchair", "coffee_table", "tv_stand", "rug"}
WORKSPACE_TYPES = {"desk", "office_chair", "bookshelf"}
DINING_TYPES   = {"dining_table", "chair", "bar_stool"}


# ─── Data helpers ─────────────────────────────────────────────────────────────

def _center(obj: dict) -> tuple[float, float]:
    x = obj.get("x", 0.0)
    z = obj.get("z", 0.0)
    return (x, z)


def _dist(a: tuple, b: tuple) -> float:
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


def _footprint(obj: dict) -> tuple[float, float]:
    """(width, depth) footprint of an object."""
    size = obj.get("size", [1.0, 1.0])
    return (float(size[0]) if size else 1.0, float(size[1]) if len(size) > 1 else 1.0)


def _aabb(obj: dict) -> tuple[float, float, float, float]:
    """Axis-aligned bounding box: (x_min, z_min, x_max, z_max)."""
    cx, cz = _center(obj)
    w, d   = _footprint(obj)
    return (cx - w / 2, cz - d / 2, cx + w / 2, cz + d / 2)


def _min_gap(a: dict, b: dict) -> float:
    """Minimum gap between two AABBs (negative means overlap)."""
    ax1, az1, ax2, az2 = _aabb(a)
    bx1, bz1, bx2, bz2 = _aabb(b)
    gap_x = max(bx1 - ax2, ax1 - bx2, 0)
    gap_z = max(bz1 - az2, az1 - bz2, 0)
    # If both gaps are 0 the boxes overlap
    if gap_x == 0 and gap_z == 0:
        # Return negative (overlap) estimate
        overlap_x = min(ax2, bx2) - max(ax1, bx1)
        overlap_z = min(az2, bz2) - max(az1, bz1)
        return -min(overlap_x, overlap_z)
    return max(gap_x, gap_z)


# ─── Dimension Scorers ────────────────────────────────────────────────────────

def score_walkability(state: dict) -> dict:
    """
    Score 0–100 based on minimum clearance gaps between all furniture pairs.
    Checks all pairs; penalises any gap below MIN_WALKWAY_M.
    """
    objects = state.get("objects", [])
    if len(objects) < 2:
        return {"score": 100, "notes": ["Room has fewer than 2 objects — no walkability concerns."]}

    violations = []
    gaps = []

    for i in range(len(objects)):
        for j in range(i + 1, len(objects)):
            gap = _min_gap(objects[i], objects[j])
            gaps.append(gap)
            if gap < MIN_WALKWAY_M:
                if gap < 0:
                    violations.append(
                        f"⛔ '{objects[i].get('type','?')}' overlaps with "
                        f"'{objects[j].get('type','?')}' (overlap {abs(gap)*100:.0f}cm)"
                    )
                else:
                    violations.append(
                        f"⚠️  Gap between '{objects[i].get('type','?')}' and "
                        f"'{objects[j].get('type','?')}' is only {gap*100:.0f}cm "
                        f"(min {MIN_WALKWAY_M*100:.0f}cm)"
                    )

    total_pairs = len(gaps)
    ok_pairs    = sum(1 for g in gaps if g >= MIN_WALKWAY_M)
    base_score  = int((ok_pairs / total_pairs) * 100) if total_pairs else 100

    notes = violations[:5] if violations else ["✅ All walkway clearances meet the 60cm minimum."]
    if len(violations) > 5:
        notes.append(f"...and {len(violations)-5} more clearance issue(s).")

    return {"score": base_score, "notes": notes, "violations": len(violations)}


def score_functional_zoning(state: dict) -> dict:
    """
    Score based on whether furniture of the same functional zone is grouped together.
    Penalises when bedroom pieces are scattered among living room pieces, etc.
    """
    objects = state.get("objects", [])
    if not objects:
        return {"score": 100, "notes": ["No furniture to evaluate."]}

    zone_centroids: dict[str, list] = {
        "bedroom": [], "living": [], "workspace": [], "dining": []
    }
    for obj in objects:
        t = obj.get("type", "")
        cx, cz = _center(obj)
        if t in BEDROOM_TYPES:
            zone_centroids["bedroom"].append((cx, cz))
        elif t in LIVING_TYPES:
            zone_centroids["living"].append((cx, cz))
        elif t in WORKSPACE_TYPES:
            zone_centroids["workspace"].append((cx, cz))
        elif t in DINING_TYPES:
            zone_centroids["dining"].append((cx, cz))

    # For each zone with ≥2 pieces, compute spread (std dev of positions)
    scores_per_zone = []
    notes = []

    for zone, pts in zone_centroids.items():
        if len(pts) < 2:
            continue
        xs = [p[0] for p in pts]
        zs = [p[1] for p in pts]
        spread = math.sqrt(_variance(xs) + _variance(zs))
        room_w = state.get("width", 4.0) or 4.0
        room_d = state.get("depth", 4.0) or 4.0
        max_spread = math.sqrt(room_w**2 + room_d**2) / 2  # half-diagonal
        zone_score = max(0, 100 - int((spread / max_spread) * 100))
        scores_per_zone.append(zone_score)
        if zone_score < 60:
            notes.append(
                f"⚠️  {zone.capitalize()} furniture is spread across the room. "
                f"Consider grouping it in one area."
            )

    if not scores_per_zone:
        return {"score": 80, "notes": ["Only one zone type detected — zoning looks OK."]}

    final_score = int(sum(scores_per_zone) / len(scores_per_zone))
    if not notes:
        notes = ["✅ Furniture zones are well-grouped."]

    return {"score": final_score, "notes": notes}


def score_visual_balance(state: dict) -> dict:
    """
    Score based on symmetry and distribution of furniture mass across the room.
    Uses centre-of-mass calculation relative to room centre.
    """
    objects = state.get("objects", [])
    if not objects:
        return {"score": 100, "notes": ["No furniture to evaluate."]}

    room_w = state.get("width", 4.0) or 4.0
    room_d = state.get("depth", 4.0) or 4.0
    room_cx, room_cz = 0.0, 0.0  # room centre is always at origin

    # Weighted centre of mass (weight by footprint area)
    total_weight = 0.0
    weighted_x   = 0.0
    weighted_z   = 0.0

    for obj in objects:
        cx, cz = _center(obj)
        w, d   = _footprint(obj)
        area   = w * d
        weighted_x   += cx * area
        weighted_z   += cz * area
        total_weight += area

    if total_weight == 0:
        return {"score": 100, "notes": ["No furniture area to evaluate."]}

    com_x = weighted_x / total_weight
    com_z = weighted_z / total_weight

    # Distance of centre of mass from room centre (normalised)
    offset = _dist((com_x, com_z), (room_cx, room_cz))
    max_offset = math.sqrt((room_w / 2) ** 2 + (room_d / 2) ** 2)
    balance_score = max(0, 100 - int((offset / max_offset) * 120))

    notes: list[str] = []
    if balance_score < 60:
        direction = []
        if com_x > 0.3:  direction.append("east")
        elif com_x < -0.3: direction.append("west")
        if com_z > 0.3:  direction.append("north")
        elif com_z < -0.3: direction.append("south")
        notes.append(
            f"⚠️  Most furniture mass is shifted {', '.join(direction) or 'off-centre'}. "
            f"Balance the layout by adding pieces on the opposite side."
        )
    else:
        notes.append("✅ Furniture distribution is visually balanced.")

    return {"score": balance_score, "notes": notes, "com": {"x": round(com_x, 2), "z": round(com_z, 2)}}


def score_object_relationships(state: dict) -> dict:
    """
    Score based on ideal spatial relationships between paired furniture:
      sofa ↔ TV, bed ↔ walls, desk ↔ window
    """
    objects = state.get("objects", [])
    windows = state.get("windows", [])
    room_w  = state.get("width",  4.0) or 4.0
    room_d  = state.get("depth",  4.0) or 4.0

    by_type: dict[str, list] = {}
    for obj in objects:
        t = obj.get("type", "?")
        by_type.setdefault(t, []).append(obj)

    penalties = []
    checks    = 0

    # 1. Sofa ↔ TV distance
    sofas    = by_type.get("sofa", []) + by_type.get("armchair", [])
    tv_stands = by_type.get("tv_stand", [])
    if sofas and tv_stands:
        checks += 1
        d = _dist(_center(sofas[0]), _center(tv_stands[0]))
        lo, hi = TV_SOFA_IDEAL
        if d < lo:
            penalties.append(f"⚠️  Sofa is too close to TV ({d:.1f}m, ideal {lo}–{hi}m).")
        elif d > hi:
            penalties.append(f"⚠️  Sofa is too far from TV ({d:.1f}m, ideal {lo}–{hi}m).")

    # 2. Bed ↔ wall proximity
    beds = by_type.get("bed", []) + by_type.get("single_bed", [])
    for bed in beds:
        checks += 1
        cx, cz = _center(bed)
        half_w, half_d = room_w / 2, room_d / 2
        dist_to_nearest_wall = min(
            abs(cx - (-half_w)), abs(cx - half_w),
            abs(cz - (-half_d)), abs(cz - half_d)
        )
        w_obj, d_obj = _footprint(bed)
        # Gap between bed edge and nearest wall
        edge_gap = dist_to_nearest_wall - max(w_obj, d_obj) / 2
        if edge_gap > BED_WALL_MAX:
            penalties.append(
                f"⚠️  Bed is floating ({edge_gap*100:.0f}cm from nearest wall). "
                "Consider placing it against a wall."
            )

    # 3. Desk ↔ window proximity
    desks = by_type.get("desk", []) + by_type.get("standing_desk", [])
    if desks and windows:
        checks += 1
        for desk in desks:
            dc = _center(desk)
            min_wd = min(_dist(dc, _window_center(w, room_w, room_d)) for w in windows)
            if min_wd > DESK_WINDOW_MAX:
                penalties.append(
                    f"⚠️  Desk is {min_wd:.1f}m from the nearest window. "
                    "Natural light improves productivity — move it closer."
                )

    if checks == 0:
        return {"score": 85, "notes": ["No paired furniture relationships to evaluate."]}

    score = max(0, 100 - len(penalties) * 20)
    notes = penalties if penalties else ["✅ Key furniture relationships look good."]
    return {"score": score, "notes": notes}


def score_natural_light(state: dict) -> dict:
    """
    Score based on whether tall furniture is blocking windows.
    Tall objects (height > 1.2m) placed within 0.5m of a window are penalised.
    """
    objects = state.get("objects", [])
    windows = state.get("windows", [])
    room_w  = state.get("width",  4.0) or 4.0
    room_d  = state.get("depth",  4.0) or 4.0

    if not windows:
        return {"score": 90, "notes": ["No windows defined — add windows for light scoring."]}

    TALL_H = 1.2
    BLOCK_RADIUS = 0.6

    blockers = []
    for obj in objects:
        if obj.get("height", 0) < TALL_H:
            continue
        cx, cz = _center(obj)
        for win in windows:
            wc = _window_center(win, room_w, room_d)
            if _dist((cx, cz), wc) < BLOCK_RADIUS:
                blockers.append(obj.get("type", "?"))

    score = max(0, 100 - len(blockers) * 30)
    notes = (
        [f"⚠️  {b} is blocking a window — move it away to maximise natural light." for b in blockers[:3]]
        or ["✅ No tall furniture is blocking the windows."]
    )
    return {"score": score, "notes": notes}


# ─── Window helpers ───────────────────────────────────────────────────────────

def _window_center(win: dict, room_w: float, room_d: float) -> tuple[float, float]:
    """Convert a wall window definition to a 2D floor-plan centre point."""
    wall = win.get("wall", "north")
    pos  = win.get("position", 0.0)  # -0.5..0.5 along wall
    half_w, half_d = room_w / 2, room_d / 2
    if wall == "north":   return (pos * room_w, -half_d)
    if wall == "south":   return (pos * room_w,  half_d)
    if wall == "east":    return ( half_w, pos * room_d)
    if wall == "west":    return (-half_w, pos * room_d)
    return (0.0, 0.0)


def _variance(vals: list[float]) -> float:
    if len(vals) < 2:
        return 0.0
    mean = sum(vals) / len(vals)
    return sum((v - mean) ** 2 for v in vals) / len(vals)


# ─── Main Scorer ──────────────────────────────────────────────────────────────

WEIGHTS = {
    "walkability":        0.25,
    "functional_zoning":  0.25,
    "visual_balance":     0.20,
    "object_relations":   0.20,
    "natural_light":      0.10,
}


def score_layout(state: dict) -> dict:
    """
    Full 5-dimension layout score for a RoomState.

    Returns:
        {
          "overall": 0-100,
          "grade":   "A" | "B" | "C" | "D" | "F",
          "dimensions": {
              "walkability":       {"score": 0-100, "weight": 0.25, "notes": [...]},
              "functional_zoning": {...},
              "visual_balance":    {...},
              "object_relations":  {...},
              "natural_light":     {...},
          },
          "summary": "Overall layout is good but ..."
        }
    """
    dims = {
        "walkability":       score_walkability(state),
        "functional_zoning": score_functional_zoning(state),
        "visual_balance":    score_visual_balance(state),
        "object_relations":  score_object_relationships(state),
        "natural_light":     score_natural_light(state),
    }

    overall = sum(
        dims[k]["score"] * WEIGHTS[k]
        for k in WEIGHTS
    )
    overall = round(overall)

    grade = (
        "A" if overall >= 85 else
        "B" if overall >= 70 else
        "C" if overall >= 55 else
        "D" if overall >= 40 else
        "F"
    )

    # Collect all actionable notes
    all_notes = []
    for dim_data in dims.values():
        for note in dim_data.get("notes", []):
            if note.startswith("⚠") or note.startswith("⛔"):
                all_notes.append(note)

    if all_notes:
        summary = f"Score {overall}/100 ({grade}). Top issues: " + " | ".join(all_notes[:2])
    else:
        summary = f"Score {overall}/100 ({grade}). Layout looks great!"

    return {
        "overall":    overall,
        "grade":      grade,
        "summary":    summary,
        "dimensions": {
            k: {"score": dims[k]["score"], "weight": WEIGHTS[k], "notes": dims[k].get("notes", [])}
            for k in dims
        },
    }

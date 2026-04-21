"""
Functional Zoning Engine — Phase 4B
=====================================
Auto-identifies functional zones in a RoomState based on furniture placement.
Returns zone polygons and zone summaries suitable for visualisation.

Zone types:
  - living_relaxation  (sofa, armchair, rug, coffee_table, tv_stand)
  - work_focus         (desk, office_chair, bookshelf)
  - sleep_rest         (bed, nightstand, wardrobe, dresser)
  - dining             (dining_table, chair, bar_stool)
  - circulation        (derived: areas with no furniture in paths)
"""

from __future__ import annotations
import math
from collections import defaultdict

# Zone membership map
ZONE_TYPES: dict[str, str] = {
    # Living
    "sofa":         "living_relaxation",
    "armchair":     "living_relaxation",
    "rug":          "living_relaxation",
    "coffee_table": "living_relaxation",
    "tv_stand":     "living_relaxation",
    "sectional_sofa": "living_relaxation",
    "loveseat":     "living_relaxation",
    # Work
    "desk":         "work_focus",
    "office_chair": "work_focus",
    "bookshelf":    "work_focus",
    "standing_desk":"work_focus",
    "monitor_stand":"work_focus",
    # Sleep
    "bed":          "sleep_rest",
    "single_bed":   "sleep_rest",
    "nightstand":   "sleep_rest",
    "wardrobe":     "sleep_rest",
    "dresser":      "sleep_rest",
    "king_bed":     "sleep_rest",
    "ottoman":      "sleep_rest",
    # Dining
    "dining_table": "dining",
    "chair":        "dining",
    "bar_stool":    "dining",
    "sideboard":    "dining",
}

ZONE_COLORS = {
    "living_relaxation": "#6366f1",  # indigo
    "work_focus":        "#f59e0b",  # amber
    "sleep_rest":        "#10b981",  # emerald
    "dining":            "#ef4444",  # red
    "circulation":       "#94a3b8",  # slate
}

ZONE_LABELS = {
    "living_relaxation": "Living / Relaxation",
    "work_focus":        "Work / Focus",
    "sleep_rest":        "Sleep / Rest",
    "dining":            "Dining",
    "circulation":       "Circulation",
}


def _center(obj: dict) -> tuple[float, float]:
    return (float(obj.get("x", 0.0)), float(obj.get("z", 0.0)))


def _dist(a: tuple, b: tuple) -> float:
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


def detect_zones(state: dict) -> dict:
    """
    Detect functional zones from RoomState furniture positions.

    Algorithm:
      1. Group furniture by zone type
      2. For each zone, compute the bounding hull (expanded by 0.6m margin)
      3. Return zone polygons + summaries

    Returns:
        {
          "zones": [
            {
              "id": "zone_living_relaxation",
              "type": "living_relaxation",
              "label": "Living / Relaxation",
              "color": "#6366f1",
              "objects": ["sofa_1", "coffee_table_1"],
              "bounds": {"x_min": -2.5, "z_min": -2.5, "x_max": 1.5, "z_max": 0.5},
              "polygon": [[x,z], ...],   # rectangle corners
              "area_m2": 12.0,
              "quality": "good" | "scattered" | "cramped",
            }
          ],
          "summary": {...},
          "recommendations": [...]
        }
    """
    objects  = state.get("objects", [])
    room_w   = state.get("width",  5.0) or 5.0
    room_d   = state.get("depth",  5.0) or 5.0

    # Group objects by zone
    by_zone: dict[str, list] = defaultdict(list)
    for obj in objects:
        zone = ZONE_TYPES.get(obj.get("type", ""), None)
        if zone:
            by_zone[zone].append(obj)

    MARGIN = 0.6  # expand zone boundary by min clearance

    zones = []
    for zone_type, zone_objs in by_zone.items():
        # Compute bounding box of all objects in this zone
        xs = [o.get("x", 0.0) for o in zone_objs]
        zs = [o.get("z", 0.0) for o in zone_objs]

        x_min = min(xs) - MARGIN
        x_max = max(xs) + MARGIN
        z_min = min(zs) - MARGIN
        z_max = max(zs) + MARGIN

        # Clamp to room bounds
        half_w, half_d = room_w / 2, room_d / 2
        x_min = max(x_min, -half_w)
        x_max = min(x_max,  half_w)
        z_min = max(z_min, -half_d)
        z_max = min(z_max,  half_d)

        area = (x_max - x_min) * (z_max - z_min)
        polygon = [
            [x_min, z_min],
            [x_max, z_min],
            [x_max, z_max],
            [x_min, z_max],
        ]

        # Quality assessment
        if len(zone_objs) == 1:
            quality = "minimal"
        else:
            # Compute spread of objects relative to zone size
            cx_list = [o.get("x", 0.0) for o in zone_objs]
            cz_list = [o.get("z", 0.0) for o in zone_objs]
            spread  = _spread(cx_list, cz_list)
            zone_diag = math.sqrt((x_max - x_min) ** 2 + (z_max - z_min) ** 2)
            quality = "scattered" if spread > zone_diag * 0.5 else "good"

        zones.append({
            "id":      f"zone_{zone_type}",
            "type":    zone_type,
            "label":   ZONE_LABELS.get(zone_type, zone_type),
            "color":   ZONE_COLORS.get(zone_type, "#888888"),
            "objects": [o.get("id", o.get("type", "?")) for o in zone_objs],
            "bounds":  {"x_min": round(x_min, 2), "z_min": round(z_min, 2),
                        "x_max": round(x_max, 2), "z_max": round(z_max, 2)},
            "polygon": [[round(p[0], 2), round(p[1], 2)] for p in polygon],
            "area_m2": round(area, 1),
            "quality": quality,
        })

    # Build recommendations
    recommendations = []
    if "living_relaxation" not in by_zone and objects:
        recommendations.append("Consider adding a sofa and coffee table to define a living zone.")
    if "work_focus" not in by_zone and objects:
        recommendations.append("No workspace detected. Add a desk to create a productivity zone.")

    scattered = [z for z in zones if z["quality"] == "scattered"]
    for z in scattered:
        recommendations.append(
            f"The {z['label']} zone is scattered — group furniture together for a cohesive feel."
        )

    summary = {
        "total_zones":    len(zones),
        "zone_types":     [z["type"] for z in zones],
        "total_area_m2":  round(sum(z["area_m2"] for z in zones), 1),
        "room_area_m2":   round(room_w * room_d, 1),
    }

    return {
        "zones":           zones,
        "summary":         summary,
        "recommendations": recommendations,
    }


def _spread(xs: list[float], zs: list[float]) -> float:
    """Mean distance from each point to the group centroid."""
    if not xs:
        return 0.0
    cx = sum(xs) / len(xs)
    cz = sum(zs) / len(zs)
    return sum(math.sqrt((x - cx) ** 2 + (z - cz) ** 2) for x, z in zip(xs, zs)) / len(xs)

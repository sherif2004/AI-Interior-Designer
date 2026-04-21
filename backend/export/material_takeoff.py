"""
Phase 5.5 — Material takeoff (MVP)
Computes basic quantities from RoomState.
"""

from __future__ import annotations


def compute_takeoff(state: dict) -> dict:
    room = state.get("room", {}) or {}
    width = float(room.get("width", 10))
    depth = float(room.get("height", 8))
    ceiling_h = float(room.get("ceiling_height", 3.0))

    floor_area_m2 = round(width * depth, 2)
    perimeter_m = round(2 * (width + depth), 2)
    wall_area_m2 = round(perimeter_m * ceiling_h, 2)

    return {
        "floor_area_m2": floor_area_m2,
        "wall_area_m2": wall_area_m2,
        "perimeter_m": perimeter_m,
        "ceiling_height_m": round(ceiling_h, 2),
        "notes": "MVP takeoff: rectangular room approximation (ignores openings).",
    }


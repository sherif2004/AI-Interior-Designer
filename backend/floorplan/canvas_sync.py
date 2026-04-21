"""
Canvas Sync — Phase 4C
========================
Converts between:
  - Fabric.js 2D canvas JSON  ↔  RoomState (3D backend format)
  - Wall polylines → 3D geometry descriptors
  - Room templates → RoomState presets

Used by:
  POST /floorplan/sync   — receive Fabric JSON, return updated RoomState actions
  GET  /templates        — list available room templates
  GET  /templates/{id}   — return a template RoomState
  POST /floorplan/walls  — receive wall data, return 3D wall descriptors
"""

from __future__ import annotations
import json
import math
from pathlib import Path
from typing import Any

PIXELS_PER_METER = 100   # 1m = 100px in canvas at 1:100 scale

# ─── Canvas JSON → RoomState Actions ─────────────────────────────────────────

def canvas_to_actions(canvas_json: dict, room_width_cm: float = 500,
                       room_depth_cm: float = 400) -> list[dict]:
    """
    Parse Fabric.js canvas JSON and return a list of RoomState actions
    that represent the new furniture positions.

    Only generates MOVE actions for objects that already exist in the room.
    Returns ADD actions for new objects drawn on the canvas.
    """
    actions = []
    objects = canvas_json.get("objects", [])
    cx_px   = canvas_json.get("width",  800) / 2
    cy_px   = canvas_json.get("height", 600) / 2

    for obj in objects:
        fp_type = obj.get("_fpType", "")

        if fp_type == "furniture":
            obj_id   = obj.get("_fpObjId", "")
            obj_type = obj.get("_fpObjType", "sofa")
            left     = obj.get("left", 0)
            top      = obj.get("top",  0)
            w_px     = obj.get("width",  100) * obj.get("scaleX", 1)
            h_px     = obj.get("height", 100) * obj.get("scaleY", 1)
            angle    = obj.get("angle", 0)

            # Centre of object in canvas pixels → metres in world space
            x_m = (left + w_px / 2 - cx_px) / PIXELS_PER_METER
            z_m = (top  + h_px / 2 - cy_px) / PIXELS_PER_METER

            if obj_id:
                actions.append({
                    "action": "MOVE",
                    "params": {
                        "id":       obj_id,
                        "x":        round(x_m, 3),
                        "z":        round(z_m, 3),
                        "rotation": round(angle, 1),
                        "source":   "floorplan_canvas",
                    }
                })
            else:
                actions.append({
                    "action": "ADD",
                    "params": {
                        "type":     obj_type,
                        "x":        round(x_m, 3),
                        "z":        round(z_m, 3),
                        "rotation": round(angle, 1),
                        "source":   "floorplan_canvas",
                    }
                })

        elif fp_type == "wall":
            # Walls drawn in canvas → add to wall list (handled by wall_builder)
            pass

    return actions


def room_state_to_canvas(state: dict) -> dict:
    """
    Convert RoomState to a Fabric.js-compatible JSON snapshot
    (list of fabric objects representing furniture footprints).

    Returns a partial Fabric JSON — the canvas will merge with existing objects.
    """
    from backend.engine.zoning import ZONE_TYPES

    room    = state.get("room", {})
    width   = room.get("width",  5.0)
    height  = room.get("height", 4.0)
    objects = state.get("objects", [])

    canvas_width  = 800
    canvas_height = 600
    cx, cy        = canvas_width / 2, canvas_height / 2

    FURNITURE_COLORS = {
        "sofa": "#6366f1", "bed": "#22d3ee", "desk": "#f59e0b",
        "chair": "#34d399", "dining_table": "#fb923c",
        "coffee_table": "#a78bfa", "wardrobe": "#f472b6",
        "tv_stand": "#60a5fa", "bookshelf": "#4ade80",
        "nightstand": "#c084fc", "lamp": "#fde68a", "rug": "#94a3b8",
    }

    fabric_objects = []
    for obj in objects:
        size = obj.get("size") or [1.0, 1.0]
        w_m  = float(size[0]) if size else 1.0
        d_m  = float(size[1]) if len(size) > 1 else 1.0
        x_m  = float(obj.get("x", 0))
        z_m  = float(obj.get("z", 0))

        w_px = w_m * PIXELS_PER_METER
        d_px = d_m * PIXELS_PER_METER
        left = cx + x_m * PIXELS_PER_METER - w_px / 2
        top  = cy + z_m * PIXELS_PER_METER - d_px / 2

        color = FURNITURE_COLORS.get(obj.get("type", ""), "#6366f1")

        fabric_objects.append({
            "type":              "rect",
            "left":              round(left, 1),
            "top":               round(top,  1),
            "width":             round(w_px, 1),
            "height":            round(d_px, 1),
            "fill":              color + "33",
            "stroke":            color,
            "strokeWidth":       2,
            "angle":             obj.get("rotation", 0),
            "selectable":        True,
            "evented":           True,
            "_fpType":           "furniture",
            "_fpObjId":          obj.get("id", ""),
            "_fpObjType":        obj.get("type", ""),
        })

    return {
        "version":         "5.3.1",
        "objects":         fabric_objects,
        "width":           canvas_width,
        "height":          canvas_height,
        "room_width_m":    width,
        "room_depth_m":    height,
    }


# ─── Room Templates ───────────────────────────────────────────────────────────

TEMPLATES: dict[str, dict] = {
    "studio_apartment": {
        "id":          "studio_apartment",
        "name":        "Studio Apartment",
        "description": "Efficient open-plan layout for a 30m² studio",
        "thumbnail":   "/static/templates/studio.png",
        "room":        {"width": 6.0, "height": 5.0, "ceiling_height": 2.7},
        "style":       {"theme": "modern", "wall_color": "#f8f8f8", "floor_type": "oak_wood"},
        "objects": [
            {"type": "bed",          "x": -1.5, "z": -1.5, "rotation": 0,  "size": [1.6, 2.1]},
            {"type": "nightstand",   "x": -0.4, "z": -1.7, "rotation": 0,  "size": [0.5, 0.4]},
            {"type": "wardrobe",     "x": -2.0, "z":  0.5, "rotation": 0,  "size": [1.2, 0.6]},
            {"type": "sofa",         "x":  0.8, "z":  0.8, "rotation": 0,  "size": [1.8, 0.85]},
            {"type": "coffee_table", "x":  0.8, "z":  1.8, "rotation": 0,  "size": [0.9, 0.5]},
            {"type": "tv_stand",     "x":  0.8, "z": -0.5, "rotation": 0,  "size": [1.2, 0.4]},
            {"type": "desk",         "x":  2.0, "z": -1.5, "rotation": 90, "size": [1.2, 0.6]},
        ],
        "windows": [{"wall": "south", "position": 0.2, "estimated_width": 1.5}],
        "doors":   [{"wall": "east",  "position": 0.0, "width": 0.9}],
    },
    "living_room": {
        "id":          "living_room",
        "name":        "Living Room",
        "description": "Two-sofa living room with TV and coffee table",
        "thumbnail":   "/static/templates/living.png",
        "room":        {"width": 5.5, "height": 4.5, "ceiling_height": 2.7},
        "style":       {"theme": "scandinavian", "wall_color": "#fafafa", "floor_type": "light_wood"},
        "objects": [
            {"type": "sofa",         "x": -0.3, "z": -1.2, "rotation": 0,   "size": [2.2, 0.9]},
            {"type": "armchair",     "x":  1.5, "z":  0.2, "rotation": -90, "size": [0.8, 0.8]},
            {"type": "coffee_table", "x": -0.3, "z":  0.2, "rotation": 0,   "size": [1.0, 0.55]},
            {"type": "tv_stand",     "x": -0.3, "z":  1.7, "rotation": 0,   "size": [1.5, 0.4]},
            {"type": "rug",          "x": -0.3, "z":  0.2, "rotation": 0,   "size": [2.5, 2.0]},
            {"type": "bookshelf",    "x":  2.0, "z":  0.8, "rotation": 90,  "size": [0.8, 0.3]},
        ],
        "windows": [{"wall": "south", "position": 0.0, "estimated_width": 2.0}],
        "doors":   [{"wall": "west",  "position": -0.3, "width": 0.9}],
    },
    "bedroom": {
        "id":          "bedroom",
        "name":        "Master Bedroom",
        "description": "King bed with walk-in wardrobe and study corner",
        "thumbnail":   "/static/templates/bedroom.png",
        "room":        {"width": 5.0, "height": 4.5, "ceiling_height": 2.7},
        "style":       {"theme": "modern", "wall_color": "#e8eaf0", "floor_type": "dark_wood"},
        "objects": [
            {"type": "bed",          "x":  0.0, "z": -1.2, "rotation": 0, "size": [1.8, 2.1]},
            {"type": "nightstand",   "x": -1.2, "z": -1.5, "rotation": 0, "size": [0.5, 0.4]},
            {"type": "nightstand",   "x":  1.2, "z": -1.5, "rotation": 0, "size": [0.5, 0.4]},
            {"type": "wardrobe",     "x": -1.5, "z":  1.3, "rotation": 0, "size": [1.2, 0.6]},
            {"type": "wardrobe",     "x":  0.2, "z":  1.3, "rotation": 0, "size": [1.2, 0.6]},
            {"type": "desk",         "x":  1.8, "z":  0.2, "rotation": 90,"size": [1.0, 0.55]},
        ],
        "windows": [{"wall": "south", "position": 0.2, "estimated_width": 1.2}],
        "doors":   [{"wall": "east",  "position": 0.0, "width": 0.9}],
    },
    "home_office": {
        "id":          "home_office",
        "name":        "Home Office",
        "description": "L-shaped desk layout with bookshelf wall",
        "thumbnail":   "/static/templates/office.png",
        "room":        {"width": 4.0, "height": 3.5, "ceiling_height": 2.7},
        "style":       {"theme": "industrial", "wall_color": "#f0ece4", "floor_type": "concrete"},
        "objects": [
            {"type": "desk",         "x": -0.5, "z": -0.8, "rotation": 0,  "size": [1.4, 0.65]},
            {"type": "desk",         "x":  0.7, "z":  0.0, "rotation": 90, "size": [1.2, 0.65]},
            {"type": "office_chair", "x": -0.5, "z":  0.2, "rotation": 0,  "size": [0.65, 0.65]},
            {"type": "bookshelf",    "x": -1.4, "z": -0.5, "rotation": 90, "size": [1.0, 0.3]},
            {"type": "bookshelf",    "x": -1.4, "z":  0.5, "rotation": 90, "size": [1.0, 0.3]},
        ],
        "windows": [{"wall": "north", "position": 0.0, "estimated_width": 1.0}],
        "doors":   [{"wall": "south", "position": 0.0, "width": 0.9}],
    },
    "open_plan": {
        "id":          "open_plan",
        "name":        "Open-Plan Living + Dining",
        "description": "Combined living and dining area for 45m² space",
        "thumbnail":   "/static/templates/open.png",
        "room":        {"width": 7.5, "height": 6.0, "ceiling_height": 3.0},
        "style":       {"theme": "modern", "wall_color": "#ffffff", "floor_type": "herringbone_oak"},
        "objects": [
            {"type": "sofa",         "x": -2.0, "z": -0.5, "rotation": 0,   "size": [2.5, 0.95]},
            {"type": "armchair",     "x":  0.2, "z":  0.5, "rotation": -90, "size": [0.85, 0.85]},
            {"type": "coffee_table", "x": -2.0, "z":  0.5, "rotation": 0,   "size": [1.2, 0.65]},
            {"type": "tv_stand",     "x": -2.0, "z":  1.8, "rotation": 0,   "size": [1.8, 0.45]},
            {"type": "rug",          "x": -1.8, "z":  0.5, "rotation": 0,   "size": [3.0, 2.5]},
            {"type": "dining_table", "x":  2.0, "z": -1.0, "rotation": 0,   "size": [1.8, 0.9]},
            {"type": "chair",        "x":  1.1, "z": -1.0, "rotation": 90,  "size": [0.5, 0.55]},
            {"type": "chair",        "x":  2.9, "z": -1.0, "rotation": -90, "size": [0.5, 0.55]},
            {"type": "chair",        "x":  2.0, "z": -1.65,"rotation": 180, "size": [0.5, 0.55]},
            {"type": "chair",        "x":  2.0, "z": -0.35,"rotation": 0,   "size": [0.5, 0.55]},
        ],
        "windows": [
            {"wall": "south", "position": -0.3, "estimated_width": 2.5},
            {"wall": "east",  "position":  0.2, "estimated_width": 1.5},
        ],
        "doors": [{"wall": "north", "position": 0.0, "width": 0.9}],
    },
}


def list_templates() -> list[dict]:
    """Return template summary cards (without full object lists)."""
    return [
        {
            "id":          t["id"],
            "name":        t["name"],
            "description": t["description"],
            "thumbnail":   t.get("thumbnail", ""),
            "object_count": len(t.get("objects", [])),
            "room_size":   f"{t['room']['width']}×{t['room']['height']}m",
        }
        for t in TEMPLATES.values()
    ]


def get_template(template_id: str) -> dict | None:
    """Return a full template RoomState preset."""
    t = TEMPLATES.get(template_id)
    if not t:
        return None
    # Add generated IDs to objects
    result = dict(t)
    objects = []
    for i, obj in enumerate(t.get("objects", [])):
        o = dict(obj)
        o.setdefault("id", f"{obj['type']}_{i+1}")
        o.setdefault("color", "#888888")
        o.setdefault("rotation", 0)
        objects.append(o)
    result["objects"] = objects
    return result

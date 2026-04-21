"""
Wall Builder — Phase 4C
========================
Converts 2D canvas wall polylines into 3D mesh descriptors
that can be consumed by the Three.js frontend renderer.

A wall is stored as:
  {
    "id":           "wall_1",
    "p1":           {"x": -2.5, "z": -2.0},    # world metres
    "p2":           {"x":  2.5, "z": -2.0},
    "thickness_m":  0.20,
    "height_m":     2.70,
    "material":     "plaster_white",
    "color":        "#faf9f6",
    "openings":     [{"type": "door"|"window", "offset_m": 0.5, "width_m": 0.9, "height_m": 2.1}]
  }

The 3D descriptor returned to the frontend contains:
  "geometry":   {position, dimensions, rotation}
  "openings":   pre-computed opening positions for CSG subtraction
"""

from __future__ import annotations
import math
from typing import Any


DEFAULT_WALL_HEIGHT = 2.70   # metres
DEFAULT_THICKNESS   = 0.15   # metres


def build_wall_geometry(wall: dict) -> dict:
    """
    Build a 3D geometry descriptor from a 2D wall definition.

    Args:
        wall: Dict with p1, p2, thickness_m, height_m, material, color, openings

    Returns:
        3D geometry descriptor suitable for THREE.BoxGeometry placement.
    """
    p1 = wall.get("p1", {})
    p2 = wall.get("p2", {})

    x1, z1 = float(p1.get("x", 0)), float(p1.get("z", 0))
    x2, z2 = float(p2.get("x", 0)), float(p2.get("z", 0))

    # Wall centre
    cx = (x1 + x2) / 2
    cz = (z1 + z2) / 2

    # Length & rotation
    dx     = x2 - x1
    dz     = z2 - z1
    length = math.sqrt(dx ** 2 + dz ** 2)
    angle  = math.degrees(math.atan2(dx, dz))   # rotation around Y

    thick  = float(wall.get("thickness_m", DEFAULT_THICKNESS))
    height = float(wall.get("height_m",    DEFAULT_WALL_HEIGHT))

    openings = _build_openings(wall.get("openings", []), length, height)

    return {
        "id":         wall.get("id", "wall"),
        "type":       "wall",
        "geometry": {
            "position":   {"x": round(cx, 3), "y": round(height / 2, 3), "z": round(cz, 3)},
            "dimensions": {"width": round(length, 3), "height": round(height, 3), "depth": round(thick, 3)},
            "rotation_y": round(angle, 2),
        },
        "material":   wall.get("material", "plaster_white"),
        "color":      wall.get("color",    "#faf9f6"),
        "length_m":   round(length, 3),
        "height_m":   round(height, 3),
        "thickness_m": round(thick, 3),
        "openings":   openings,
        "p1_world":   {"x": x1, "z": z1},
        "p2_world":   {"x": x2, "z": z2},
    }


def _build_openings(openings: list, wall_length: float, wall_height: float) -> list[dict]:
    """Compute opening positions relative to wall start for CSG subtraction."""
    result = []
    for op in openings:
        op_type = op.get("type", "door")
        offset  = float(op.get("offset_m", 0))
        width   = float(op.get("width_m",  0.9 if op_type == "door" else 1.2))
        height  = float(op.get("height_m", 2.1 if op_type == "door" else 1.2))
        sill    = float(op.get("sill_m",   0.0 if op_type == "door" else 0.9))

        result.append({
            "type":      op_type,
            "offset_m":  round(offset, 3),
            "width_m":   round(width,  3),
            "height_m":  round(height, 3),
            "sill_m":    round(sill,   3),
            # Local position along wall (from wall centre)
            "local_x":   round(offset + width / 2 - wall_length / 2, 3),
            "local_y":   round(sill + height / 2, 3),
        })
    return result


def build_walls(wall_data_list: list[dict]) -> dict:
    """
    Process a list of raw wall dicts and return all 3D descriptors + a summary.
    """
    geometries = [build_wall_geometry(w) for w in wall_data_list]

    total_length = sum(g["length_m"] for g in geometries)
    total_area   = sum(g["length_m"] * g["height_m"] for g in geometries)

    return {
        "walls":        geometries,
        "wall_count":   len(geometries),
        "total_length_m": round(total_length, 2),
        "total_area_m2":  round(total_area,   2),
    }


def generate_floor_polygon(walls: list[dict]) -> list[dict]:
    """Extract floor polygon vertices from ordered closed loop walls."""
    # Assumes walls are drawn in order forming a closed loop
    polygon = []
    for w in walls:
        polygon.append(w["p1"])
    return polygon


def infer_walls_from_room(width_m: float, depth_m: float,
                          height_m: float = DEFAULT_WALL_HEIGHT,
                          thickness_m: float = DEFAULT_THICKNESS,
                          doors: list | None = None,
                          windows: list | None = None,
                          shape: str = "rectangle") -> dict:
    """
    Auto-generate perimeter walls and floor polygon from room dimensions and shape.
    """
    hw = width_m / 2
    hd = depth_m / 2

    if shape == "L_shape":
        # Cutout top-right quadrant
        base_walls = [
            {"id": "wall_south", "face": "south", "p1": {"x":  hw, "z":  hd}, "p2": {"x": -hw, "z":  hd}},
            {"id": "wall_west",  "face": "west",  "p1": {"x": -hw, "z":  hd}, "p2": {"x": -hw, "z": -hd}},
            {"id": "wall_north1","face": "north", "p1": {"x": -hw, "z": -hd}, "p2": {"x":  0,  "z": -hd}},
            {"id": "wall_east1", "face": "east",  "p1": {"x":  0,  "z": -hd}, "p2": {"x":  0,  "z":  0}},
            {"id": "wall_north2","face": "north", "p1": {"x":  0,  "z":  0},  "p2": {"x":  hw, "z":  0}},
            {"id": "wall_east2", "face": "east",  "p1": {"x":  hw, "z":  0},  "p2": {"x":  hw, "z":  hd}},
        ]
    elif shape == "T_shape":
        # T-shape: wide top, narrow bottom
        w3 = hw / 1.5
        base_walls = [
            {"id": "wall_north", "face": "north", "p1": {"x": -hw, "z": -hd}, "p2": {"x":  hw, "z": -hd}},
            {"id": "wall_east1", "face": "east",  "p1": {"x":  hw, "z": -hd}, "p2": {"x":  hw, "z":  0}},
            {"id": "wall_south1","face": "south", "p1": {"x":  hw, "z":  0},  "p2": {"x":  w3, "z":  0}},
            {"id": "wall_east2", "face": "east",  "p1": {"x":  w3, "z":  0},  "p2": {"x":  w3, "z":  hd}},
            {"id": "wall_south2","face": "south", "p1": {"x":  w3, "z":  hd}, "p2": {"x": -w3, "z":  hd}},
            {"id": "wall_west1", "face": "west",  "p1": {"x": -w3, "z":  hd}, "p2": {"x": -w3, "z":  0}},
            {"id": "wall_south3","face": "south", "p1": {"x": -w3, "z":  0},  "p2": {"x": -hw, "z":  0}},
            {"id": "wall_west2", "face": "west",  "p1": {"x": -hw, "z":  0},  "p2": {"x": -hw, "z": -hd}},
        ]
    else:
        # Default rectangle
        base_walls = [
            {"id": "wall_north", "face": "north", "p1": {"x": -hw, "z": -hd}, "p2": {"x":  hw, "z": -hd}},
            {"id": "wall_east",  "face": "east",  "p1": {"x":  hw, "z": -hd}, "p2": {"x":  hw, "z":  hd}},
            {"id": "wall_south", "face": "south", "p1": {"x":  hw, "z":  hd}, "p2": {"x": -hw, "z":  hd}},
            {"id": "wall_west",  "face": "west",  "p1": {"x": -hw, "z":  hd}, "p2": {"x": -hw, "z": -hd}},
        ]

    # Map openings to walls by face
    opening_map: dict[str, list] = {w["face"]: [] for w in base_walls}

    for door in (doors or []):
        face = door.get("wall", "east")
        if face in opening_map:
            opening_map[face].append({
                "type":      "door",
                "offset_m":  float(door.get("position", 0)) + width_m / 2,
                "width_m":   float(door.get("width", 0.9)),
                "height_m":  2.1,
            })

    for win in (windows or []):
        face = win.get("wall", "south")
        if face in opening_map:
            opening_map[face].append({
                "type":      "window",
                "offset_m":  float(win.get("position", 0)) + (width_m if face in ("north", "south") else depth_m) / 2,
                "width_m":   float(win.get("estimated_width", 1.2)),
                "height_m":  1.2,
                "sill_m":    0.9,
            })

    walls = []
    for bw in base_walls:
        wall = {
            **bw,
            "thickness_m": thickness_m,
            "height_m":    height_m,
            "material":    "plaster_white",
            "color":       "#faf9f6",
            "openings":    opening_map.get(bw["face"], []),
        }
        walls.append(wall)

    return {
        "walls": walls,
        "floor_polygon": generate_floor_polygon(walls)
    }


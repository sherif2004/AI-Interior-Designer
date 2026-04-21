"""
What-If Engine — Phase 4B
==========================
Simulates layout changes without committing to the actual RoomState.
Lets users preview the score delta and clearance impact of proposed actions
before confirming them.

Usage:
    result = simulate(current_state, proposed_actions)
    # result.score_before, result.score_after, result.delta, result.conflicts
"""

from __future__ import annotations
import copy
import math
from typing import Any

from backend.engine.layout_scorer import score_layout


def simulate(state: dict, actions: list[dict]) -> dict:
    """
    Apply a list of actions to a *copy* of the room state and return
    before/after scores plus a list of predicted conflicts.

    Args:
        state:   Current RoomState dict (not modified)
        actions: List of action dicts, same format as /command endpoint

    Returns:
        {
            "score_before":    int,
            "score_after":     int,
            "delta":           int,   // positive = improvement
            "grade_before":    "B",
            "grade_after":     "A",
            "conflicts":       [...], // collisions in simulated state
            "clearance_delta": int,   // change in walkability score
            "simulated_state": {...}, // preview state (not saved)
            "actions_applied": int,
        }
    """
    # Score before
    before = score_layout(state)

    # Deep copy to avoid mutating the real state
    sim_state = copy.deepcopy(state)

    applied = 0
    conflicts: list[str] = []

    for action in actions:
        action_type = (action.get("action") or action.get("type") or "").upper()
        params       = action.get("params", action)

        try:
            if action_type == "ADD":
                new_obj = _build_object(params, sim_state)
                collision = _check_collision(new_obj, sim_state.get("objects", []))
                if collision:
                    conflicts.append(
                        f"ADD {params.get('type','?')} at ({params.get('x',0):.1f},"
                        f"{params.get('z',0):.1f}) conflicts with {collision}"
                    )
                sim_state.setdefault("objects", []).append(new_obj)
                applied += 1

            elif action_type == "MOVE":
                obj_id = params.get("id")
                for obj in sim_state.get("objects", []):
                    if obj.get("id") == obj_id:
                        obj["x"] = params.get("x", obj["x"])
                        obj["z"] = params.get("z", obj["z"])
                        collision = _check_collision(obj, [
                            o for o in sim_state.get("objects", []) if o.get("id") != obj_id
                        ])
                        if collision:
                            conflicts.append(f"MOVE {obj_id} → conflicts with {collision}")
                        applied += 1
                        break

            elif action_type == "ROTATE":
                obj_id = params.get("id")
                for obj in sim_state.get("objects", []):
                    if obj.get("id") == obj_id:
                        obj["rotation"] = params.get("rotation", 0)
                        applied += 1
                        break

            elif action_type == "DELETE":
                obj_id = params.get("id")
                sim_state["objects"] = [
                    o for o in sim_state.get("objects", [])
                    if o.get("id") != obj_id
                ]
                applied += 1

            elif action_type == "SET_ROOM_STYLE":
                sim_state.setdefault("style", {})["theme"] = params.get("style", "")
                applied += 1

            elif action_type == "SET_WALL_STYLE":
                for k, v in params.items():
                    sim_state.setdefault("style", {})[f"wall_{k}"] = v
                applied += 1

            elif action_type == "SET_FLOOR_STYLE":
                for k, v in params.items():
                    sim_state.setdefault("style", {})[f"floor_{k}"] = v
                applied += 1

        except Exception as e:
            conflicts.append(f"Error applying {action_type}: {e}")

    # Score after simulation
    after = score_layout(sim_state)

    walkability_before = before["dimensions"]["walkability"]["score"]
    walkability_after  = after["dimensions"]["walkability"]["score"]

    return {
        "score_before":     before["overall"],
        "score_after":      after["overall"],
        "delta":            after["overall"] - before["overall"],
        "grade_before":     before["grade"],
        "grade_after":      after["grade"],
        "conflicts":        conflicts,
        "clearance_delta":  walkability_after - walkability_before,
        "actions_applied":  applied,
        "simulated_state":  sim_state,
        "dimensions_before": before["dimensions"],
        "dimensions_after":  after["dimensions"],
    }


# ─── Helpers ──────────────────────────────────────────────────────────────────

_OBJ_COUNTER = 0


def _build_object(params: dict, state: dict) -> dict:
    global _OBJ_COUNTER
    _OBJ_COUNTER += 1

    furniture_type = params.get("type", "sofa")
    default_sizes  = {
        "sofa":          [2.2, 0.9],
        "bed":           [1.6, 2.1],
        "desk":          [1.2, 0.6],
        "dining_table":  [1.4, 0.85],
        "wardrobe":      [1.2, 0.6],
        "chair":         [0.5, 0.55],
        "coffee_table":  [1.0, 0.55],
        "tv_stand":      [1.5, 0.4],
        "lamp":          [0.4, 0.4],
        "bookshelf":     [0.8, 0.3],
        "nightstand":    [0.5, 0.4],
        "office_chair":  [0.65, 0.65],
        "rug":           [2.0, 3.0],
    }
    size = default_sizes.get(furniture_type, [1.0, 1.0])

    return {
        "id":       params.get("id", f"sim_{furniture_type}_{_OBJ_COUNTER}"),
        "type":     furniture_type,
        "x":        float(params.get("x", 0.0)),
        "z":        float(params.get("z", 0.0)),
        "y":        0.0,
        "rotation": float(params.get("rotation", 0.0)),
        "color":    params.get("color", "#888888"),
        "size":     params.get("size", size),
        "height":   params.get("height", 0.85),
    }


def _check_collision(obj: dict, others: list[dict]) -> str:
    """Return name of first conflicting object, or empty string if none."""
    ax1, az1, ax2, az2 = _aabb(obj)

    for other in others:
        bx1, bz1, bx2, bz2 = _aabb(other)
        overlap_x = ax1 < bx2 and ax2 > bx1
        overlap_z = az1 < bz2 and az2 > bz1
        if overlap_x and overlap_z:
            return other.get("type", "?")

    return ""


def _aabb(obj: dict) -> tuple[float, float, float, float]:
    cx = float(obj.get("x", 0.0))
    cz = float(obj.get("z", 0.0))
    size = obj.get("size", [1.0, 1.0])
    w = float(size[0]) if size else 1.0
    d = float(size[1]) if len(size) > 1 else 1.0
    return (cx - w / 2, cz - d / 2, cx + w / 2, cz + d / 2)

"""
MOVE action handler — moves an existing furniture item.
"""
from backend.planner.spatial_rules import apply_direction
from backend.planner.constraint_solver import solve
from backend.state.state_manager import RoomState


def handle_move(state: RoomState, action: dict) -> RoomState:
    """Move an existing object in a direction by some amount."""
    target = action.get("target", "last")
    direction = action.get("direction", "right")
    amount = float(action.get("amount", 0.5))

    objects = list(state.get("objects", []))
    room = state["room"]

    obj, idx = _resolve_target(target, objects, state.get("last_action", {}), state.get("selected_object_id", ""))
    if obj is None:
        return {**state, "error": f"Could not find object: '{target}'"}

    new_x, new_z = apply_direction(obj, direction, amount, room)

    # Check collision at new position (excluding the object itself)
    new_x, new_z, error = solve(new_x, new_z, obj["w"], obj["d"], room, objects, exclude_id=obj["id"])
    if error:
        return {**state, "error": f"Cannot move {obj['id']}: {error}"}

    updated = {**obj, "x": round(new_x, 3), "z": round(new_z, 3)}
    objects[idx] = updated

    return {
        **state,
        "objects": objects,
        "last_action": {"type": "MOVE", "object_id": obj["id"]},
        "selected_object_id": obj["id"],
        "message": f"↔️ Moved {obj['id']} {direction} by {amount}m to ({new_x:.1f}, {new_z:.1f}).",
        "error": None,
    }


def _resolve_target(target: str, objects: list, last_action: dict, selected_object_id: str = ""):
    """Returns (object_dict, index) or (None, -1)."""
    if not objects:
        return None, -1

    if target in ("selected", "it") and selected_object_id:
        for i, o in enumerate(objects):
            if o["id"] == selected_object_id:
                return o, i

    if target == "last":
        last_id = last_action.get("object_id", "")
        for i, o in enumerate(objects):
            if o["id"] == last_id:
                return o, i
        return objects[-1], len(objects) - 1

    # Exact ID match
    for i, o in enumerate(objects):
        if o["id"].lower() == target:
            return o, i

    # Type match (first found)
    for i, o in enumerate(objects):
        if o["type"].lower() == target or target in o["type"].lower():
            return o, i

    return None, -1

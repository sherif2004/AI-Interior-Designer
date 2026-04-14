"""
ROTATE action handler — rotates an existing furniture item.
"""
from backend.planner.constraint_solver import solve
from backend.state.state_manager import RoomState


def handle_rotate(state: RoomState, action: dict) -> RoomState:
    """Rotate an object by N degrees (90 increments). Swaps w/d for 90/270."""
    target = action.get("target", "last")
    degrees = int(action.get("degrees", 90))

    objects = list(state.get("objects", []))
    room = state["room"]

    obj, idx = _resolve_target(target, objects, state.get("last_action", {}))
    if obj is None:
        return {**state, "error": f"Could not find object: '{target}'"}

    new_rotation = (obj.get("rotation", 0) + degrees) % 360

    # Swap dimensions for 90° / 270°
    if degrees % 180 != 0:
        new_w, new_d = obj["d"], obj["w"]
    else:
        new_w, new_d = obj["w"], obj["d"]

    # Re-validate position with new dimensions
    new_x, new_z, error = solve(
        obj["x"], obj["z"], new_w, new_d, room, objects, exclude_id=obj["id"]
    )
    if error:
        return {**state, "error": f"Cannot rotate {obj['id']}: {error}"}

    updated = {**obj, "rotation": new_rotation, "w": new_w, "d": new_d, "x": new_x, "z": new_z}
    objects[idx] = updated

    return {
        **state,
        "objects": objects,
        "last_action": {"type": "ROTATE", "object_id": obj["id"]},
        "message": f"🔄 Rotated {obj['id']} by {degrees}° (now {new_rotation}°).",
        "error": None,
    }


def _resolve_target(target, objects, last_action):
    if not objects:
        return None, -1
    if target == "last":
        last_id = last_action.get("object_id", "")
        for i, o in enumerate(objects):
            if o["id"] == last_id:
                return o, i
        return objects[-1], len(objects) - 1
    for i, o in enumerate(objects):
        if o["id"].lower() == target:
            return o, i
    for i, o in enumerate(objects):
        if o["type"].lower() == target or target in o["type"].lower():
            return o, i
    return None, -1

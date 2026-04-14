"""
DELETE action handler — removes a furniture item from the room.
"""
from backend.state.state_manager import RoomState


def handle_delete(state: RoomState, action: dict) -> RoomState:
    """Remove an object by ID or type."""
    target = action.get("target", "")
    objects = list(state.get("objects", []))

    if not objects:
        return {**state, "error": "The room is already empty."}

    obj, idx = _resolve_target(target, objects, state.get("last_action", {}))
    if obj is None:
        return {**state, "error": f"Could not find object to delete: '{target}'"}

    objects.pop(idx)

    return {
        **state,
        "objects": objects,
        "last_action": {"type": "DELETE", "object_id": obj["id"]},
        "message": f"🗑️ Removed {obj['id']} from the room.",
        "error": None,
    }


def _resolve_target(target, objects, last_action):
    if not objects:
        return None, -1
    if target in ("last", "it"):
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

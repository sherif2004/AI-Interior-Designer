"""
ADD action handler — places a new furniture item in the room.
"""
from backend.environment.objects import get_furniture, resolve_type, FURNITURE_CATALOG
from backend.planner.spatial_rules import resolve_placement
from backend.planner.constraint_solver import solve
from backend.state.state_manager import RoomState


def handle_add(state: RoomState, action: dict) -> RoomState:
    """
    Add a new furniture object to the room.
    Resolves type, finds position, checks constraints, updates state.
    """
    raw_type = action.get("object", "")
    furniture_type = resolve_type(raw_type)
    furniture_def = get_furniture(furniture_type)
    custom_def = action.get("custom_definition") or {}

    if not furniture_def and custom_def:
        furniture_def = {
            "size": custom_def.get("size", [1.0, 1.0]),
            "color": custom_def.get("color", "#888888"),
            "height": custom_def.get("height", 0.8),
            "description": custom_def.get("description", furniture_type),
        }

    if not furniture_def:
        known = ", ".join(list(FURNITURE_CATALOG.keys())[:10]) + "..."
        return {**state, "error": f"Unknown furniture type: '{raw_type}'. Try: {known}"}

    constraints = action.get("constraints", {})
    placement = constraints.get("placement", "auto")
    reference_id = constraints.get("reference_id")

    # Get base size (may be swapped by rotation)
    w, d = furniture_def["size"]
    room = state["room"]
    objects = state.get("objects", [])

    # Resolve symbolic placement to coordinates, unless explicit coordinates were provided
    if action.get("x") is not None and action.get("z") is not None:
        x = float(action["x"])
        z = float(action["z"])
    else:
        x, z = resolve_placement(placement, room, objects, w, d, reference_id)

    # Run constraint solver (collision detection + nudge)
    x, z, error = solve(x, z, w, d, room, objects)
    if error:
        return {**state, "error": error}

    # Generate unique ID
    count = sum(1 for o in objects if o["type"] == furniture_type)
    obj_id = f"{furniture_type}_{count + 1}"

    new_obj = {
        "id": obj_id,
        "type": furniture_type,
        "x": round(x, 3),
        "z": round(z, 3),
        "w": w,
        "d": d,
        "rotation": int(action.get("rotation", 0)) % 360,
        "color": furniture_def.get("color", "#888888"),
        "height": furniture_def.get("height", 0.8),
        "description": furniture_def.get("description", furniture_type),
        "source": action.get("source", "catalog"),
        "product_id": action.get("product_id"),
        "product_name": action.get("product_name"),
        "image_url": action.get("image_url"),
        "price": action.get("price"),
        "brand": action.get("brand"),
    }

    new_objects = objects + [new_obj]
    last_action = {"type": "ADD", "object_id": obj_id}

    return {
        **state,
        "objects": new_objects,
        "last_action": last_action,
        "selected_object_id": obj_id,
        "selected_product_id": action.get("product_id", state.get("selected_product_id", "")),
        "message": f"✅ Added {furniture_def['description']} ({obj_id}) at position ({x:.1f}, {z:.1f}).",
        "error": None,
    }

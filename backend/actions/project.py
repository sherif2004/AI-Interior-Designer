"""
Project persistence and room structure actions.
"""
from __future__ import annotations

from copy import deepcopy

from backend.state.state_manager import RoomState, default_state
from backend.storage.project_store import save_project, load_project


def handle_set_room_dimensions(state: RoomState, action: dict) -> RoomState:
    room = deepcopy(state.get("room", {}))
    width = float(action.get("width", room.get("width", 10.0)))
    height = float(action.get("height", room.get("height", 8.0)))
    ceiling_height = float(action.get("ceiling_height", room.get("ceiling_height", 3.0)))

    room["width"] = max(2.0, width)
    room["height"] = max(2.0, height)
    room["ceiling_height"] = max(2.2, ceiling_height)

    return {
        **state,
        "room": room,
        "last_action": {"type": "SET_ROOM_DIMENSIONS", "object_id": "room"},
        "message": f"📐 Updated room size to {room['width']:.1f}m × {room['height']:.1f}m, ceiling {room['ceiling_height']:.1f}m.",
        "error": None,
    }

def handle_set_room_shape(state: RoomState, action: dict) -> RoomState:
    room = deepcopy(state.get("room", {}))
    shape = str(action.get("shape", "rectangle")).strip()
    width = float(action.get("width", room.get("width", 10.0)))
    height = float(action.get("height", room.get("height", 8.0)))

    room["shape"] = shape
    room["width"] = max(2.0, width)
    room["height"] = max(2.0, height)
    
    # We leverage backend/floorplan/wall_builder here to embed walls directly into the state
    from backend.floorplan.wall_builder import infer_walls_from_room
    inferred = infer_walls_from_room(room["width"], room["height"], shape=shape)
    room["walls"] = inferred["walls"]
    room["floor_polygon"] = inferred["floor_polygon"]

    return {
        **state,
        "room": room,
        "last_action": {"type": "SET_ROOM_SHAPE", "object_id": shape},
        "message": f"📐 Set room shape to '{shape}' ({room['width']:.1f}m × {room['height']:.1f}m).",
        "error": None,
    }


def handle_add_opening(state: RoomState, action: dict, opening_type: str) -> RoomState:
    room = deepcopy(state.get("room", {}))
    collection_key = "windows" if opening_type == "window" else "doors"
    collection = list(room.get(collection_key, []))

    wall = str(action.get("wall", "north")).lower().strip()
    position = float(action.get("position", 0.5))
    width = float(action.get("width", 1.2 if opening_type == "window" else 0.9))

    opening = {
        "wall": wall,
        "position": min(0.95, max(0.05, position)),
        "width": max(0.4, width),
    }
    collection.append(opening)
    room[collection_key] = collection

    return {
        **state,
        "room": room,
        "last_action": {"type": f"ADD_{opening_type.upper()}", "object_id": collection_key},
        "message": f"🪟 Added {opening_type} on the {wall} wall.",
        "error": None,
    }


def handle_save_project(state: RoomState, action: dict) -> RoomState:
    room = deepcopy(state.get("room", {}))
    project = deepcopy(state.get("project", {}))

    project_id = str(action.get("project_id") or project.get("id") or "default_project").strip().replace(" ", "_")
    project_name = str(action.get("project_name") or project.get("name") or "My Home Project").strip()
    project["id"] = project_id
    project["name"] = project_name
    room["project_id"] = project_id
    room["project_name"] = project_name

    updated_state = {**state, "project": project, "room": room}
    saved_id = save_project(updated_state, project_id)

    return {
        **updated_state,
        "last_action": {"type": "SAVE_PROJECT", "object_id": saved_id},
        "message": f"💾 Saved project '{project_name}' as {saved_id}.",
        "error": None,
    }


def handle_load_project(state: RoomState, action: dict) -> RoomState:
    project_id = str(action.get("project_id", "default_project")).strip().replace(" ", "_")
    loaded = load_project(project_id)
    loaded.setdefault("project", {"id": project_id, "name": project_id.replace("_", " ").title()})
    loaded["message"] = f"📂 Loaded project '{loaded['project'].get('name', project_id)}'."
    loaded["error"] = None
    loaded["last_action"] = {"type": "LOAD_PROJECT", "object_id": project_id}
    return loaded


def handle_new_project(state: RoomState, action: dict) -> RoomState:
    width = float(action.get("width", 10.0))
    height = float(action.get("height", 8.0))
    fresh = default_state(width, height)
    project_name = str(action.get("project_name", "My Home Project")).strip()
    project_id = str(action.get("project_id", project_name.lower().replace(" ", "_"))).strip()
    fresh["project"] = {"id": project_id, "name": project_name}
    fresh["room"]["project_id"] = project_id
    fresh["room"]["project_name"] = project_name
    fresh["message"] = f"🆕 Started a new project: {project_name}."
    return fresh


def handle_select_object(state: RoomState, action: dict) -> RoomState:
    target = str(action.get("target", "")).lower().strip()
    objects = list(state.get("objects", []))
    if not objects:
        return {**state, "error": "No objects in the room to select."}

    for obj in objects:
        if obj["id"].lower() == target or obj["type"].lower() == target or target in obj["id"].lower() or target in obj["type"].lower():
            return {
                **state,
                "selected_object_id": obj["id"],
                "last_action": {"type": "SELECT_OBJECT", "object_id": obj["id"]},
                "message": f"🎯 Selected {obj['id']}.",
                "error": None,
            }

    return {**state, "error": f"Could not find object to select: '{target}'"}

"""
Style and layout action handlers.
"""
from __future__ import annotations

from copy import deepcopy

from backend.actions.add import handle_add
from backend.state.state_manager import RoomState

COLOR_MAP = {
    "white": "#f5f5f5",
    "off_white": "#f2efe8",
    "warm_white": "#f3efe8",
    "beige": "#e6d7c3",
    "cream": "#f4ead8",
    "sand": "#d8c3a5",
    "taupe": "#b8a99a",
    "gray": "#9aa0a6",
    "light_gray": "#c7ccd4",
    "dark_gray": "#4b5563",
    "charcoal": "#374151",
    "blue": "#6b8db5",
    "navy": "#334155",
    "teal": "#3c6e71",
    "green": "#7aa27a",
    "sage": "#a3b18a",
    "olive": "#7c8b5a",
    "brown": "#8b6b4a",
    "oak": "#b08968",
    "light_oak": "#c9b79c",
    "walnut": "#6f4e37",
    "espresso": "#4a3428",
    "black": "#2b2b2b",
    "terracotta": "#c97b63",
    "marble": "#d9d9d9",
    "ivory": "#f6f1e7",
    "greige": "#b7b1a7",
}

THEME_PRESETS = {
    "modern": {
        "wall_style": {"name": "warm_white", "color": "#f3efe8", "material": "paint", "label": "warm white paint"},
        "floor_style": {"name": "oak", "color": "#b08968", "material": "wood", "label": "oak wood"},
    },
    "minimalist": {
        "wall_style": {"name": "white", "color": "#f5f5f5", "material": "paint", "label": "white paint"},
        "floor_style": {"name": "light_oak", "color": "#c9b79c", "material": "wood", "label": "light oak wood"},
    },
    "scandinavian": {
        "wall_style": {"name": "off_white", "color": "#f8f5ef", "material": "paint", "label": "soft white paint"},
        "floor_style": {"name": "light_oak", "color": "#d2b48c", "material": "wood", "label": "natural oak wood"},
    },
    "cozy": {
        "wall_style": {"name": "cream", "color": "#eadcc8", "material": "paint", "label": "cream paint"},
        "floor_style": {"name": "walnut", "color": "#8b6b4a", "material": "wood", "label": "walnut wood"},
    },
    "luxury": {
        "wall_style": {"name": "greige", "color": "#d6d3d1", "material": "paint", "label": "silk gray paint"},
        "floor_style": {"name": "marble", "color": "#d9d9d9", "material": "marble", "label": "marble floor"},
    },
    "industrial": {
        "wall_style": {"name": "charcoal", "color": "#4b5563", "material": "concrete", "label": "charcoal concrete"},
        "floor_style": {"name": "espresso", "color": "#4a3428", "material": "wood", "label": "dark wood floor"},
    },
    "bohemian": {
        "wall_style": {"name": "sand", "color": "#d8c3a5", "material": "paint", "label": "sand paint"},
        "floor_style": {"name": "terracotta", "color": "#c97b63", "material": "tile", "label": "terracotta tile"},
    },
}

ROOM_TEMPLATES = {
    "bedroom": [
        {"type": "bed", "placement": "against_wall_south", "rotation": 180},
        {"type": "nightstand", "placement": "next_to:bed_1"},
        {"type": "nightstand", "placement": "next_to:bed_1"},
        {"type": "wardrobe", "placement": "against_wall_west"},
        {"type": "dresser", "placement": "against_wall_north"},
        {"type": "rug", "placement": "center"},
        {"type": "lamp", "placement": "corner"},
        {"type": "plant", "placement": "auto"},
    ],
    "living_room": [
        {"type": "sofa", "placement": "against_wall_south", "rotation": 180},
        {"type": "coffee_table", "placement": "in_front_of:sofa_1"},
        {"type": "tv_stand", "placement": "against_wall_north"},
        {"type": "armchair", "placement": "corner"},
        {"type": "rug", "placement": "center"},
        {"type": "lamp", "placement": "next_to:sofa_1"},
        {"type": "plant", "placement": "corner"},
    ],
    "office": [
        {"type": "desk", "placement": "against_wall_north"},
        {"type": "office_chair", "placement": "in_front_of:desk_1"},
        {"type": "bookshelf", "placement": "against_wall_west"},
        {"type": "lamp", "placement": "next_to:desk_1"},
        {"type": "plant", "placement": "corner"},
        {"type": "rug", "placement": "center"},
    ],
    "dining_room": [
        {"type": "dining_table", "placement": "center"},
        {"type": "chair", "placement": "north_of:dining_table_1"},
        {"type": "chair", "placement": "south_of:dining_table_1"},
        {"type": "chair", "placement": "east_of:dining_table_1"},
        {"type": "chair", "placement": "west_of:dining_table_1"},
        {"type": "dresser", "placement": "against_wall_west"},
        {"type": "lamp", "placement": "corner"},
    ],
}


def _normalize_color(value: str | None, fallback: str) -> str:
    if not value:
        return fallback
    normalized = value.lower().strip().replace(" ", "_")
    if normalized.startswith("#"):
        return normalized
    return COLOR_MAP.get(normalized, fallback)


def _label(color: str | None, material: str | None, default: str) -> str:
    parts = [p for p in [color, material] if p]
    return " ".join(parts) if parts else default


def handle_set_wall_style(state: RoomState, action: dict) -> RoomState:
    room = deepcopy(state.get("room", {}))
    style = dict(room.get("wall_style", {}))

    color_name = action.get("color", style.get("name", "white"))
    material = action.get("material", style.get("material", "paint"))
    style["name"] = color_name
    style["color"] = _normalize_color(color_name, style.get("color", "#f5f5f5"))
    style["material"] = material
    style["label"] = _label(color_name, material, "painted wall")

    room["wall_style"] = style
    if action.get("theme"):
        room["theme"] = action["theme"]

    return {
        **state,
        "room": room,
        "last_action": {"type": "SET_WALL_STYLE", "object_id": "room"},
        "message": f"🎨 Updated walls to {style['label']}.",
        "error": None,
    }


def handle_set_floor_style(state: RoomState, action: dict) -> RoomState:
    room = deepcopy(state.get("room", {}))
    style = dict(room.get("floor_style", {}))

    color_name = action.get("color", style.get("name", "oak"))
    material = action.get("material", style.get("material", "wood"))
    style["name"] = color_name
    style["color"] = _normalize_color(color_name, style.get("color", "#b08968"))
    style["material"] = material
    style["label"] = _label(color_name, material, "styled floor")

    room["floor_style"] = style
    if action.get("theme"):
        room["theme"] = action["theme"]

    return {
        **state,
        "room": room,
        "last_action": {"type": "SET_FLOOR_STYLE", "object_id": "room"},
        "message": f"🪵 Updated floor to {style['label']}.",
        "error": None,
    }


def handle_set_room_style(state: RoomState, action: dict) -> RoomState:
    theme = str(action.get("theme", "modern")).lower().strip().replace(" ", "_")
    preset = THEME_PRESETS.get(theme)
    if not preset:
        return {**state, "error": f"Unknown room style/theme: '{theme}'"}

    room = deepcopy(state.get("room", {}))
    room["theme"] = theme
    room["wall_style"] = dict(preset["wall_style"])
    room["floor_style"] = dict(preset["floor_style"])

    return {
        **state,
        "room": room,
        "last_action": {"type": "SET_ROOM_STYLE", "object_id": "room"},
        "message": f"✨ Applied {theme.replace('_', ' ')} room style.",
        "error": None,
    }


def _apply_rotation(state: RoomState, object_id: str, degrees: int) -> RoomState:
    if not degrees:
        return state
    objects = list(state.get("objects", []))
    for idx, obj in enumerate(objects):
        if obj["id"] == object_id:
            updated = dict(obj)
            updated["rotation"] = degrees % 360
            if degrees % 180 != 0:
                updated["w"], updated["d"] = obj["d"], obj["w"]
            objects[idx] = updated
            return {**state, "objects": objects, "last_action": {"type": "ROTATE", "object_id": object_id}}
    return state


def _theme_adjustments(theme: str | None, room_type: str) -> list[dict]:
    theme = (theme or "").lower()
    adjustments = []
    if room_type == "living_room" and theme in {"cozy", "bohemian"}:
        adjustments.append({"type": "lamp", "placement": "auto"})
    if room_type == "bedroom" and theme in {"luxury", "modern"}:
        adjustments.append({"type": "rug", "placement": "center"})
    if room_type == "office" and theme in {"industrial", "modern"}:
        adjustments.append({"type": "bookshelf", "placement": "against_wall_east"})
    return adjustments


def handle_generate_layout(state: RoomState, action: dict) -> RoomState:
    room_type = str(action.get("room_type", "bedroom")).lower().strip().replace(" ", "_")
    template = ROOM_TEMPLATES.get(room_type)
    if not template:
        return {**state, "error": f"Unknown room type: '{room_type}'"}

    working_state: RoomState = {
        **state,
        "objects": [],
        "last_action": {},
        "error": None,
    }

    theme = action.get("theme")
    if theme:
        themed = handle_set_room_style(working_state, {"theme": theme})
        if themed.get("error"):
            return themed
        working_state = themed

    final_template = list(template) + _theme_adjustments(str(theme or working_state.get("room", {}).get("theme", "")), room_type)

    for item in final_template:
        placement = item.get("placement", "auto")
        working_state = handle_add(
            working_state,
            {
                "object": item["type"],
                "constraints": {"placement": placement},
            },
        )
        if working_state.get("error"):
            return {
                **working_state,
                "message": f"⚠️ Could not fully generate the layout for {room_type.replace('_', ' ')}.",
            }

        if item.get("rotation"):
            object_id = working_state.get("last_action", {}).get("object_id")
            if object_id:
                working_state = _apply_rotation(working_state, object_id, int(item["rotation"]))

    room = deepcopy(working_state.get("room", {}))
    room["room_type"] = room_type
    if theme:
        room["theme"] = str(theme).lower().strip().replace(" ", "_")

    return {
        **working_state,
        "room": room,
        "last_action": {"type": "GENERATE_LAYOUT", "object_id": room_type},
        "message": f"🏠 Created a {room.get('theme', 'custom').replace('_', ' ')} {room_type.replace('_', ' ')} layout with styled walls and flooring.",
        "error": None,
    }

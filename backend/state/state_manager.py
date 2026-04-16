"""
LangGraph RoomState definition — the single source of truth passed through all graph nodes.
"""
from __future__ import annotations
from typing import TypedDict, Optional, Any


class RoomState(TypedDict, total=False):
    # Project metadata
    project: dict               # {id, name}

    # Core room geometry
    room: dict                  # {width, height, wall_thickness, doors, windows, wall_style, floor_style, theme}

    # All currently placed furniture objects
    objects: list[dict]         # [{id, type, x, z, w, d, rotation, color, height}]

    # Conversation / session history
    history: list[str]          # past user commands

    # The most recent parsed action from the LLM
    pending_action: dict        # {type, object, constraints, target_id, direction, degrees}

    # Most recent successfully executed action
    last_action: dict

    # Human-readable response to send back to the user
    message: str

    # Error message (if any node fails); drives retry logic
    error: Optional[str]

    # Raw user command that triggered this graph run
    user_command: str

    # How many times the LLM planner has been retried for this command
    retry_count: int


def default_state(room_width: float = 10.0, room_height: float = 8.0) -> RoomState:
    """Return an initial empty room state."""
    return RoomState(
        project={
            "id": "default_project",
            "name": "My Home Project",
        },
        room={
            "width": room_width,
            "height": room_height,
            "wall_thickness": 0.2,
            "doors": [{"wall": "south", "position": 0.5, "width": 0.9}],
            "windows": [
                {"wall": "north", "position": 0.3, "width": 1.2},
                {"wall": "east",  "position": 0.6, "width": 1.0},
            ],
            "wall_style": {
                "name": "warm white",
                "color": "#f3efe8",
                "material": "paint",
                "label": "warm white paint",
            },
            "floor_style": {
                "name": "oak",
                "color": "#b08968",
                "material": "wood",
                "label": "oak wood",
            },
            "theme": "modern",
            "room_type": "generic",
            "ceiling_height": 3.0,
            "project_id": "default_project",
            "project_name": "My Home Project",
        },
        objects=[],
        history=[],
        pending_action={},
        last_action={},
        message="Room is ready. What would you like to add?",
        error=None,
        user_command="",
        retry_count=0,
    )

"""
Robust LLM response parser — extracts and validates JSON actions.
"""
import json
import re
from typing import Optional

VALID_TYPES = {
    "ADD", "MOVE", "ROTATE", "DELETE", "RESET", "ERROR",
    "SET_WALL_STYLE", "SET_FLOOR_STYLE", "SET_ROOM_STYLE", "GENERATE_LAYOUT",
    "SET_ROOM_DIMENSIONS", "ADD_WINDOW", "ADD_DOOR", "SAVE_PROJECT", "LOAD_PROJECT", "NEW_PROJECT",
}

REQUIRED_FIELDS = {
    "ADD":             ["object", "constraints"],
    "MOVE":            ["target", "direction"],
    "ROTATE":          ["target", "degrees"],
    "DELETE":          ["target"],
    "RESET":           [],
    "SET_WALL_STYLE":  [],
    "SET_FLOOR_STYLE": [],
    "SET_ROOM_STYLE":    ["theme"],
    "GENERATE_LAYOUT":   ["room_type"],
    "SET_ROOM_DIMENSIONS": [],
    "ADD_WINDOW":        [],
    "ADD_DOOR":          [],
    "SAVE_PROJECT":      [],
    "LOAD_PROJECT":      ["project_id"],
    "NEW_PROJECT":       [],
    "ERROR":             ["reason"],
}


def extract_json(text: str) -> Optional[str]:
    """Extract JSON from LLM text, stripping markdown fences and extra prose."""
    text = text.strip()

    # Try direct parse first
    if text.startswith("{"):
        return text

    # Strip ```json ... ``` fences
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        return fence_match.group(1)

    # Extract first JSON object found
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        return brace_match.group(0)

    return None


def parse_action(llm_response: str) -> dict:
    """
    Parse LLM response into a validated action dict.
    Returns a dict with at minimum {"type": ...}.
    On failure, returns {"type": "ERROR", "reason": "<parse failure reason>"}.
    """
    raw_json = extract_json(llm_response)
    if not raw_json:
        return {
            "type": "ERROR",
            "reason": f"Could not extract JSON from LLM response: {llm_response[:200]}"
        }

    try:
        action = json.loads(raw_json)
    except json.JSONDecodeError as e:
        return {
            "type": "ERROR",
            "reason": f"JSON decode error: {e}. Raw: {raw_json[:200]}"
        }

    # Validate type field
    action_type = str(action.get("type", "")).upper()
    if action_type not in VALID_TYPES:
        return {
            "type": "ERROR",
            "reason": f"Unknown action type: {action.get('type')}. Must be one of {VALID_TYPES}"
        }
    action["type"] = action_type

    # Validate required fields
    missing = [f for f in REQUIRED_FIELDS[action_type] if f not in action]
    if missing:
        return {
            "type": "ERROR",
            "reason": f"Action {action_type} missing required fields: {missing}"
        }

    # Normalize common fields
    if action_type == "ADD":
        action["object"] = action["object"].lower().replace(" ", "_")
        if not isinstance(action.get("constraints"), dict):
            action["constraints"] = {"placement": "auto"}
        if "placement" not in action["constraints"]:
            action["constraints"]["placement"] = "auto"

    if action_type in ("MOVE", "ROTATE", "DELETE"):
        action["target"] = str(action["target"]).lower().strip()

    if action_type == "MOVE":
        action["direction"] = str(action.get("direction", "right")).lower()
        try:
            action["amount"] = float(action.get("amount", 0.5))
        except (TypeError, ValueError):
            action["amount"] = 0.5

    if action_type == "ROTATE":
        try:
            action["degrees"] = int(action.get("degrees", 90))
        except (TypeError, ValueError):
            action["degrees"] = 90

    if action_type in ("SET_WALL_STYLE", "SET_FLOOR_STYLE"):
        if "color" in action and isinstance(action["color"], str):
            action["color"] = action["color"].lower().strip().replace(" ", "_")
        if "material" in action and isinstance(action["material"], str):
            action["material"] = action["material"].lower().strip().replace(" ", "_")
        if "theme" in action and isinstance(action["theme"], str):
            action["theme"] = action["theme"].lower().strip().replace(" ", "_")

    if action_type in ("SET_ROOM_STYLE", "GENERATE_LAYOUT"):
        if "theme" in action and isinstance(action["theme"], str):
            action["theme"] = action["theme"].lower().strip().replace(" ", "_")
        if "room_type" in action and isinstance(action["room_type"], str):
            action["room_type"] = action["room_type"].lower().strip().replace(" ", "_")

    if action_type == "SET_ROOM_DIMENSIONS":
        for field in ("width", "height", "ceiling_height"):
            if field in action:
                try:
                    action[field] = float(action[field])
                except (TypeError, ValueError):
                    action.pop(field, None)

    if action_type in ("ADD_WINDOW", "ADD_DOOR"):
        if "wall" in action and isinstance(action["wall"], str):
            action["wall"] = action["wall"].lower().strip()
        for field in ("position", "width"):
            if field in action:
                try:
                    action[field] = float(action[field])
                except (TypeError, ValueError):
                    action.pop(field, None)

    if action_type in ("SAVE_PROJECT", "LOAD_PROJECT", "NEW_PROJECT"):
        for field in ("project_id", "project_name"):
            if field in action and isinstance(action[field], str):
                action[field] = action[field].strip().replace(" ", "_") if field == "project_id" else action[field].strip()

    return action

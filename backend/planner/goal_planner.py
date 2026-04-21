"""
Goal Planner — Phase 4B
=======================
Accepts high-level user design goals and generates multi-step action plans.
Uses the LLM to reason about the goal, then the constraint engine to validate.

Supported goals:
  "Make this room cozy"
  "Optimize this layout for a family of 4"
  "I need a home office that fits in this corner"
  "Fix all clearance issues"
  "Create a Scandinavian bedroom"
"""

from __future__ import annotations
import json
import logging
import os
from typing import Any

log = logging.getLogger("goal_planner")


GOAL_SYSTEM_PROMPT = """You are an expert interior designer AI.
Given the current room state and a user goal, generate a multi-step action plan
to achieve that goal. Each step must be one of the supported room actions.

SUPPORTED ACTIONS:
- ADD: {type, x, z, rotation, color} — place new furniture
- MOVE: {id, x, z} — reposition existing furniture
- ROTATE: {id, rotation} — change furniture orientation
- DELETE: {id} — remove furniture
- SET_ROOM_STYLE: {style} — apply theme (modern, scandinavian, industrial, etc.)
- SET_WALL_STYLE: {color, material}
- SET_FLOOR_STYLE: {material}
- SET_ROOM_SHAPE: {shape, width, height} — shape can be rectangle, L_shape, or T_shape

OUTPUT FORMAT (JSON only, no prose):
{
  "goal_summary": "one sentence describing the plan",
  "steps": [
    {"action": "ACTION_NAME", "params": {...}, "reason": "why this step"},
    ...
  ],
  "expected_improvements": ["clearance +20%", "zones separated", ...]
}

ROOM COORDINATES: origin at room centre, +X=east, +Z=north. 1 unit = 1 metre.
BE REALISTIC: don't add furniture outside room bounds. Check provided room dimensions.
PRIORITISE: clearance violations first, then aesthetics.
"""


def plan_goal(
    goal: str,
    state: dict,
    llm_client=None,
    model: str = "",
) -> dict:
    """
    Generate a multi-step action plan for a high-level goal.

    Args:
        goal:       Natural language goal string
        state:      Current RoomState dict
        llm_client: OpenRouter-compatible client (or None for mock)
        model:      LLM model string

    Returns:
        {
            "goal": str,
            "goal_summary": str,
            "steps": [...],
            "expected_improvements": [...],
            "raw_response": str
        }
    """
    if llm_client is None:
        return _mock_plan(goal, state)

    room_summary = _summarise_room(state)

    messages = [
        {"role": "system", "content": GOAL_SYSTEM_PROMPT},
        {"role": "user", "content": (
            f"GOAL: {goal}\n\n"
            f"CURRENT ROOM:\n{room_summary}\n\n"
            "Generate an action plan to achieve this goal."
        )},
    ]

    try:
        response = llm_client.chat.completions.create(
            model=model or os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat"),
            messages=messages,
            temperature=0.4,
            max_tokens=1500,
        )
        content = response.choices[0].message.content.strip()

        # Parse JSON from response
        plan = _extract_json(content)
        plan["goal"] = goal
        plan["raw_response"] = content
        return plan

    except Exception as e:
        log.error(f"Goal planner LLM error: {e}")
        return {
            "goal": goal,
            "goal_summary": f"Could not generate plan: {e}",
            "steps": [],
            "expected_improvements": [],
            "error": str(e),
        }


def _summarise_room(state: dict) -> str:
    """Create a compact text summary of the room state for the LLM."""
    w = state.get("width", 4.0)
    d = state.get("depth", 4.0)
    h = state.get("ceiling_height", 2.7)
    objects = state.get("objects", [])
    style   = state.get("style", {})

    lines = [
        f"Room: {w}m wide × {d}m deep × {h}m ceiling",
        f"Style: {style.get('theme', 'none')}, walls={style.get('wall_color','?')}, floor={style.get('floor_type','?')}",
        f"Furniture ({len(objects)} items):",
    ]
    for obj in objects[:20]:  # Cap at 20 to avoid token bloat
        lines.append(
            f"  - {obj.get('type','?')} id={obj.get('id','?')} "
            f"at ({obj.get('x',0):.1f}, {obj.get('z',0):.1f}) "
            f"rot={obj.get('rotation',0)}°"
        )
    if len(objects) > 20:
        lines.append(f"  ... and {len(objects)-20} more items")

    windows = state.get("windows", [])
    doors   = state.get("doors", [])
    if windows:
        lines.append(f"Windows: {len(windows)} (walls: {[w.get('wall') for w in windows]})")
    if doors:
        lines.append(f"Doors: {len(doors)} (walls: {[d.get('wall') for d in doors]})")

    return "\n".join(lines)


def _extract_json(text: str) -> dict:
    """Extract JSON object from LLM response (handles code fences)."""
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strip code fences
    for fence in ("```json", "```"):
        if fence in text:
            start = text.find(fence) + len(fence)
            end   = text.rfind("```")
            if end > start:
                try:
                    return json.loads(text[start:end].strip())
                except json.JSONDecodeError:
                    pass

    # Find first { ... }
    start = text.find("{")
    end   = text.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass

    return {"goal_summary": "Could not parse plan.", "steps": [], "expected_improvements": []}


def _mock_plan(goal: str, state: dict) -> dict:
    """Return a mock plan when no LLM client is available."""
    goal_lower = goal.lower()
    steps = []

    if "cozy" in goal_lower or "warm" in goal_lower:
        steps = [
            {"action": "SET_ROOM_STYLE", "params": {"style": "scandinavian"},
             "reason": "Scandinavian style creates a cozy, warm atmosphere"},
            {"action": "SET_WALL_STYLE", "params": {"color": "#f5f0e8", "material": "plaster"},
             "reason": "Warm off-white walls feel welcoming"},
            {"action": "SET_FLOOR_STYLE", "params": {"material": "oak_wood"},
             "reason": "Warm wood flooring adds coziness"},
        ]
        improvements = ["Warmer colour palette", "Cohesive Scandinavian theme"]
    elif "office" in goal_lower or "work" in goal_lower:
        steps = [
            {"action": "ADD", "params": {"type": "desk", "x": 0, "z": -1.5, "rotation": 0},
             "reason": "Central desk for workspace"},
            {"action": "ADD", "params": {"type": "office_chair", "x": 0, "z": -0.5, "rotation": 0},
             "reason": "Ergonomic chair at desk"},
            {"action": "ADD", "params": {"type": "bookshelf", "x": 2, "z": -1.5, "rotation": 90},
             "reason": "Storage and organisation"},
        ]
        improvements = ["Defined workspace zone", "Improved productivity layout"]
    elif "modern" in goal_lower or "minimalist" in goal_lower:
        steps = [
            {"action": "SET_ROOM_STYLE", "params": {"style": "modern"},
             "reason": "Modern minimalist theme"},
            {"action": "SET_FLOOR_STYLE", "params": {"material": "concrete"},
             "reason": "Industrial concrete floor suits modern aesthetic"},
        ]
        improvements = ["Cleaner minimalist look", "Modern aesthetic applied"]
    else:
        steps = [
            {"action": "SET_ROOM_STYLE", "params": {"style": "modern"},
             "reason": "Applying a coherent modern theme"},
        ]
        improvements = ["Cohesive room theme applied"]

    return {
        "goal":                 goal,
        "goal_summary":         f"Plan to: {goal}",
        "steps":                steps,
        "expected_improvements": improvements,
        "raw_response":         "(mock response — no LLM client connected)",
    }

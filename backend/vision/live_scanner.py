"""
Live Room Scanner — Phase 4A / 5.1
====================================
Processes base64 camera frames (or uploaded photos) via LLM vision
to extract partial or full room state information.

Used by:
  POST /scan/frame  — live camera frame → partial state update (Phase 4A)
  POST /import/photo — full room photo → complete RoomState (Phase 5.1)
"""

from __future__ import annotations
import base64
import json
import logging
import os
import re
from typing import Any

log = logging.getLogger("live_scanner")

SCAN_SYSTEM_PROMPT = """You are an expert interior design AI with computer vision capability.
Analyse the provided room/furniture image and extract structured information.

Extract the following information from the image (estimate if exact values are not visible):
1. Room dimensions (width x depth in metres, estimate from perspective)
2. Ceiling height estimate
3. Wall colour and finish
4. Floor material and colour
5. Visible furniture items (type, approximate position, colour, style)
6. Doors and windows (which wall, approximate position)

OUTPUT FORMAT (JSON only, no prose):
{
  "room_dimensions": {"width": 4.0, "depth": 5.0, "ceiling_height": 2.7},
  "wall_style": {"color": "#f5f0e8", "material": "plaster"},
  "floor_style": {"material": "wood", "color": "#c4a882"},
  "furniture": [
    {"type": "sofa", "color": "#6b7280", "style": "modern", "position": "north_wall",
     "approximate_x": -1.0, "approximate_z": -1.5}
  ],
  "windows": [{"wall": "south", "position": 0.0, "estimated_width": 1.5}],
  "doors":   [{"wall": "east",  "position": 0.2}],
  "style":   "modern",
  "confidence": 0.75,
  "notes": "Room appears to be a living room with natural lighting from south"
}

POSITION SYSTEM: x=0, z=0 is room centre. +x=east, +z=north. Values in metres.
POSITION SHORTHAND: use "north_wall"→z≈-depth/2, "south_wall"→z≈+depth/2, etc.
If you cannot determine a value, use null.
"""


def scan_frame(
    image_data: str,
    llm_client=None,
    model: str = "",
    partial: bool = True,
) -> dict:
    """
    Analyse a base64-encoded image and return extracted room information.

    Args:
        image_data: Base64 image string (with or without data: prefix)
        llm_client: OpenRouter client (or None for mock)
        model:      Vision-capable model string
        partial:    If True, only return confirmed items (for live scanning)

    Returns:
        {
            "room_dimensions": {...} | None,
            "furniture": [...],
            "wall_style": {...} | None,
            "floor_style": {...} | None,
            "windows": [...],
            "doors": [...],
            "style": str,
            "confidence": float,
            "notes": str,
            "actions": [...]  ← ready-to-apply RoomState actions
        }
    """
    if llm_client is None:
        return _mock_scan(image_data)

    # Normalise base64 data
    if "base64," in image_data:
        image_data = image_data.split("base64,", 1)[1]

    vision_model = model or os.getenv("OPENROUTER_MODEL", "google/gemini-flash-1.5")

    messages = [
        {"role": "system", "content": SCAN_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_data}",
                        "detail": "high"
                    }
                },
                {
                    "type": "text",
                    "text": "Analyse this room image and extract structured room state information."
                }
            ]
        }
    ]

    try:
        response = llm_client.chat.completions.create(
            model=vision_model,
            messages=messages,
            temperature=0.2,
            max_tokens=1200,
        )
        content = response.choices[0].message.content.strip()
        result  = _extract_json(content)
        result["raw_response"] = content

        # Build ready-to-apply actions
        result["actions"] = _build_actions(result, partial=partial)
        return result

    except Exception as e:
        log.error(f"Vision scan error: {e}")
        return {
            "error":      str(e),
            "furniture":  [],
            "windows":    [],
            "doors":      [],
            "actions":    [],
            "confidence": 0.0,
        }


def _build_actions(scan_result: dict, partial: bool = True) -> list[dict]:
    """Convert scan result into RoomState actions."""
    actions = []
    confidence = scan_result.get("confidence", 0.5)

    # Only apply high-confidence results in partial (live) mode
    threshold = 0.6 if partial else 0.3

    if confidence < threshold:
        return []

    # Room dimensions
    dims = scan_result.get("room_dimensions")
    if dims and dims.get("width") and dims.get("depth"):
        actions.append({
            "action": "SET_ROOM_DIMENSIONS",
            "params": {
                "width":          dims["width"],
                "depth":          dims["depth"],
                "ceiling_height": dims.get("ceiling_height", 2.7),
            }
        })

    # Wall style
    wall = scan_result.get("wall_style")
    if wall and wall.get("color"):
        actions.append({
            "action": "SET_WALL_STYLE",
            "params": wall
        })

    # Floor style
    floor = scan_result.get("floor_style")
    if floor and floor.get("material"):
        actions.append({
            "action": "SET_FLOOR_STYLE",
            "params": floor
        })

    # Furniture (only add if high confidence)
    for item in scan_result.get("furniture", []):
        if item.get("type"):
            actions.append({
                "action": "ADD",
                "params": {
                    "type":   item["type"],
                    "x":      item.get("approximate_x", 0.0),
                    "z":      item.get("approximate_z", 0.0),
                    "color":  item.get("color", "#888888"),
                    "source": "vision_scan",
                }
            })

    return actions


def _extract_json(text: str) -> dict:
    """Extract JSON from LLM response."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    for fence in ("```json", "```"):
        if fence in text:
            start = text.find(fence) + len(fence)
            end   = text.rfind("```")
            if end > start:
                try:
                    return json.loads(text[start:end].strip())
                except Exception:
                    pass
    start = text.find("{")
    end   = text.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end])
        except Exception:
            pass
    return {"furniture": [], "windows": [], "doors": [], "confidence": 0.0}


def _mock_scan(image_data: str) -> dict:
    """Return a mock scan result when no LLM client is available."""
    return {
        "room_dimensions": {"width": 4.5, "depth": 5.0, "ceiling_height": 2.7},
        "wall_style":      {"color": "#f5f0e8", "material": "plaster"},
        "floor_style":     {"material": "wood", "color": "#c4a882"},
        "furniture": [
            {"type": "sofa", "color": "#6b7280", "approximate_x": -0.5, "approximate_z": -1.5},
        ],
        "windows": [{"wall": "south", "position": 0.0, "estimated_width": 1.2}],
        "doors":   [{"wall": "east",  "position": 0.0}],
        "style":   "modern",
        "confidence": 0.5,
        "notes":   "Mock scan result (no LLM client connected)",
        "actions": [],
        "raw_response": "(mock)",
    }

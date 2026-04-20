"""
Blueprint parser — uploads a 2D floor plan image and extracts room dimensions,
doors, and windows using AI vision (LLM) or basic heuristics.
"""
from __future__ import annotations
import os
import json
import base64
import urllib.request
import urllib.error
from pathlib import Path


def parse_blueprint(image_bytes: bytes, filename: str) -> dict:
    """
    Parse a floor plan image and return a partial room state dict.
    Uses the OpenRouter LLM vision API if available, else basic heuristics.
    """
    provider = os.getenv("OPENROUTER_MODEL", "")
    api_key = os.getenv("OPENROUTER_API_KEY", "")

    if api_key:
        return _parse_with_llm(image_bytes, filename, api_key)
    else:
        return _parse_heuristic(image_bytes, filename)


def _parse_with_llm(image_bytes: bytes, filename: str, api_key: str) -> dict:
    """Use LLM vision API to extract room data from a blueprint image."""
    b64_image = base64.b64encode(image_bytes).decode("utf-8")
    ext = Path(filename).suffix.lower().lstrip(".")
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "pdf": "application/pdf"}.get(ext, "image/png")

    system_prompt = (
        "You are an expert architect and interior design analyst. "
        "Analyze the provided floor plan image and extract room dimensions and layout information. "
        "Respond ONLY in valid JSON with this exact schema:\n"
        "{\n"
        '  "width": <float, room width in meters>,\n'
        '  "height": <float, room depth in meters>,\n'
        '  "ceiling_height": <float, estimated ceiling height, default 2.8>,\n'
        '  "room_type": <string: "bedroom"|"living_room"|"office"|"dining_room"|"generic">,\n'
        '  "doors": [{"wall": "north|south|east|west", "position": <0.0-1.0>, "width": <meters>}],\n'
        '  "windows": [{"wall": "north|south|east|west", "position": <0.0-1.0>, "width": <meters>}],\n'
        '  "notes": "<brief description of the floor plan>"\n'
        "}\n"
        "If you cannot determine a value, use a sensible default."
    )

    payload = json.dumps({
        "model": os.getenv("OPENROUTER_MODEL", "anthropic/claude-3-haiku"),
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": "Please analyze this floor plan and extract room information."},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64_image}"}},
            ],
        }],
        "temperature": 0.1,
        "max_tokens": 512,
    }).encode("utf-8")

    url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/") + "/chat/completions"
    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Content-Type", "application/json")
    req.add_header("HTTP-Referer", "http://localhost:8000")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
        text = result["choices"][0]["message"]["content"]
        # Extract JSON from response
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            parsed = json.loads(text[start:end])
            return _normalize_parsed(parsed)
        return _parse_heuristic(image_bytes, filename)
    except Exception:
        return _parse_heuristic(image_bytes, filename)


def _parse_heuristic(image_bytes: bytes, filename: str) -> dict:
    """
    Basic heuristic parser — returns a default room with metadata.
    Used as fallback when no LLM is available.
    """
    # Try to use image dimensions as a hint for aspect ratio
    width = 6.0
    height = 5.0

    try:
        # Quick PNG/JPEG header read for pixel dimensions
        if image_bytes[:8] == b'\x89PNG\r\n\x1a\n':
            px_w = int.from_bytes(image_bytes[16:20], 'big')
            px_h = int.from_bytes(image_bytes[20:24], 'big')
            if px_w > 0 and px_h > 0:
                ratio = px_w / px_h
                height = round(min(max(width / ratio, 3.0), 12.0), 1)
    except Exception:
        pass

    return {
        "width": width,
        "height": height,
        "ceiling_height": 2.8,
        "room_type": "generic",
        "doors": [{"wall": "south", "position": 0.5, "width": 0.9}],
        "windows": [{"wall": "north", "position": 0.4, "width": 1.2}],
        "notes": (
            f"Blueprint imported from '{filename}'. "
            "Dimensions are estimated — please adjust with voice commands like 'Make the room 8 by 6 meters'."
        ),
        "heuristic": True,
    }


def _normalize_parsed(data: dict) -> dict:
    """Normalize and clamp parsed blueprint data."""
    return {
        "width": max(3.0, min(float(data.get("width", 6.0)), 20.0)),
        "height": max(3.0, min(float(data.get("height", 5.0)), 20.0)),
        "ceiling_height": max(2.2, min(float(data.get("ceiling_height", 2.8)), 5.0)),
        "room_type": str(data.get("room_type", "generic")),
        "doors": data.get("doors", [{"wall": "south", "position": 0.5, "width": 0.9}]),
        "windows": data.get("windows", [{"wall": "north", "position": 0.4, "width": 1.2}]),
        "notes": data.get("notes", "Blueprint imported via AI analysis."),
        "heuristic": False,
    }

"""
AI Photoreal Image Renderer — generates room scene prompts and calls image generation APIs.
Supports Stability AI, Replicate (SDXL), and a mock mode for offline use.
"""
from __future__ import annotations
import os
import json
import base64
import urllib.request
import urllib.error
from typing import Optional


def build_render_prompt(state: dict) -> str:
    """Generate a rich photorealistic rendering prompt from room state."""
    room = state.get("room", {})
    objects = state.get("objects", [])

    theme = room.get("theme", "modern").replace("_", " ")
    wall_label = room.get("wall_style", {}).get("label", "white walls")
    floor_label = room.get("floor_style", {}).get("label", "wood floor")
    ceiling_h = room.get("ceiling_height", 3.0)
    rw = room.get("width", 10)
    rh = room.get("height", 8)

    furniture_list = ", ".join(
        set(o.get("type", "item").replace("_", " ") for o in objects)
    ) or "an empty room"

    prompt = (
        f"Photorealistic interior design render of a {theme} style room, "
        f"{rw:.0f} by {rh:.0f} meters, {ceiling_h:.1f}m ceiling height. "
        f"Featuring {wall_label}, {floor_label}. "
        f"Furniture includes {furniture_list}. "
        f"Professional architectural photography, golden hour lighting, "
        f"sharp focus, 8K resolution, hyper-realistic, warm ambient lighting, "
        f"interior design magazine quality, depth of field."
    )
    return prompt


def render_image(state: dict) -> dict:
    """
    Generate a photoreal render image from room state.
    Returns {success, image_url, image_b64, prompt, provider}.
    """
    prompt = build_render_prompt(state)
    provider = os.getenv("IMAGE_RENDER_PROVIDER", "mock").lower()

    if provider == "stability":
        return _call_stability(prompt)
    elif provider == "replicate":
        return _call_replicate(prompt)
    else:
        return _mock_render(prompt)


def _call_stability(prompt: str) -> dict:
    """Call Stability AI Stable Image Core API."""
    api_key = os.getenv("STABILITY_API_KEY", "")
    if not api_key:
        return {"success": False, "error": "STABILITY_API_KEY not set", "prompt": prompt}

    url = "https://api.stability.ai/v2beta/stable-image/generate/core"
    boundary = "----FormBoundary7MA4YWxkTrZu0gW"
    body_parts = [
        f"--{boundary}",
        'Content-Disposition: form-data; name="prompt"',
        "",
        prompt,
        f"--{boundary}",
        'Content-Disposition: form-data; name="output_format"',
        "",
        "png",
        f"--{boundary}",
        'Content-Disposition: form-data; name="aspect_ratio"',
        "",
        "16:9",
        f"--{boundary}--",
    ]
    body = "\r\n".join(body_parts).encode("utf-8")

    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Accept", "image/*")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            img_bytes = resp.read()
        b64 = base64.b64encode(img_bytes).decode("utf-8")
        return {
            "success": True,
            "image_b64": b64,
            "image_url": None,
            "prompt": prompt,
            "provider": "stability",
        }
    except urllib.error.HTTPError as e:
        return {"success": False, "error": f"Stability HTTP {e.code}: {e.read().decode()}", "prompt": prompt}
    except Exception as e:
        return {"success": False, "error": str(e), "prompt": prompt}


def _call_replicate(prompt: str) -> dict:
    """Call Replicate SDXL API."""
    api_key = os.getenv("REPLICATE_API_KEY", "")
    if not api_key:
        return {"success": False, "error": "REPLICATE_API_KEY not set", "prompt": prompt}

    # Start prediction
    start_url = "https://api.replicate.com/v1/models/stability-ai/sdxl/predictions"
    payload = json.dumps({
        "input": {
            "prompt": prompt,
            "width": 1344,
            "height": 768,
            "num_inference_steps": 30,
            "guidance_scale": 7.5,
        }
    }).encode("utf-8")

    req = urllib.request.Request(start_url, data=payload, method="POST")
    req.add_header("Authorization", f"Token {api_key}")
    req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        poll_url = data.get("urls", {}).get("get", "")
        if not poll_url:
            return {"success": False, "error": "No poll URL from Replicate", "prompt": prompt}

        # Poll for result (up to 90 seconds)
        import time
        for _ in range(18):
            time.sleep(5)
            req2 = urllib.request.Request(poll_url)
            req2.add_header("Authorization", f"Token {api_key}")
            with urllib.request.urlopen(req2, timeout=10) as r2:
                result = json.loads(r2.read().decode())
            if result.get("status") == "succeeded":
                img_url = result.get("output", [None])[0]
                return {"success": True, "image_url": img_url, "image_b64": None, "prompt": prompt, "provider": "replicate"}
            if result.get("status") in ("failed", "canceled"):
                return {"success": False, "error": result.get("error", "Prediction failed"), "prompt": prompt}

        return {"success": False, "error": "Replicate timed out", "prompt": prompt}
    except Exception as e:
        return {"success": False, "error": str(e), "prompt": prompt}


def _mock_render(prompt: str) -> dict:
    """
    Mock render — returns a placeholder Unsplash interior image URL.
    Useful for local development without an API key.
    """
    # Use a real, high-quality interior design photo from Unsplash
    mock_url = "https://images.unsplash.com/photo-1618221195710-dd6b41faaea6?w=1344&h=768&fit=crop&auto=format"
    return {
        "success": True,
        "image_url": mock_url,
        "image_b64": None,
        "prompt": prompt,
        "provider": "mock",
        "note": "Set IMAGE_RENDER_PROVIDER=stability or replicate in .env for real renders",
    }

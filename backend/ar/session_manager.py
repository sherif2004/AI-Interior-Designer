"""
AR Session Manager — Phase 4D
==============================
Manages AR placement sessions with token-based access.
Each session holds AR-placed furniture that can later be committed to RoomState.

Sessions are persisted as JSON in data/ar_sessions/.
QR code generation uses the `qrcode` library (pip install qrcode[pil]).
"""

from __future__ import annotations
import json
import logging
import os
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger("ar_session_manager")

DATA_DIR    = Path("data")
SESSION_DIR = DATA_DIR / "ar_sessions"
SESSION_DIR.mkdir(parents=True, exist_ok=True)

SESSION_TTL_SECONDS = 3600  # 1 hour


def _session_path(token: str) -> Path:
    safe = "".join(c for c in token if c.isalnum())[:64]
    return SESSION_DIR / f"{safe}.json"


# ─── Session CRUD ─────────────────────────────────────────────────────────────

def create_session(room_state: dict | None = None) -> dict:
    """Create a new AR session. Returns the session dict with token."""
    token = secrets.token_urlsafe(16)
    session = {
        "token":      token,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": datetime.now(timezone.utc).timestamp() + SESSION_TTL_SECONDS,
        "room_state": room_state or {},
        "ar_placements": [],   # list of {product_id, x, y, z, rotation, scale}
        "captures":     [],    # list of {type: photo|video, url, ts}
        "status":       "active",
    }
    _session_path(token).write_text(
        json.dumps(session, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    log.info(f"AR session created: {token}")
    return session


def get_session(token: str) -> dict | None:
    """Load a session by token. Returns None if not found or expired."""
    path = _session_path(token)
    if not path.exists():
        return None
    try:
        session = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

    if time.time() > session.get("expires_at", 0):
        session["status"] = "expired"
    return session


def save_session(session: dict):
    """Persist session to disk."""
    token = session.get("token", "")
    if not token:
        return
    _session_path(token).write_text(
        json.dumps(session, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def place_product(token: str, product_id: str, x: float, y: float, z: float,
                  rotation: float = 0.0, scale: float = 1.0) -> dict:
    """Add an AR product placement to the session."""
    session = get_session(token)
    if not session:
        return {"error": "session_not_found"}

    placement = {
        "id":         f"ar_{product_id}_{int(time.time())}",
        "product_id": product_id,
        "x": x, "y": y, "z": z,
        "rotation":   rotation,
        "scale":      scale,
        "placed_at":  datetime.now(timezone.utc).isoformat(),
    }
    session["ar_placements"].append(placement)
    save_session(session)
    return placement


def save_capture(token: str, capture_type: str, data_url: str) -> dict:
    """Save an AR screenshot or video recording metadata."""
    session = get_session(token)
    if not session:
        return {"error": "session_not_found"}

    capture_id = f"cap_{int(time.time())}"
    capture = {
        "id":       capture_id,
        "type":     capture_type,  # "photo" or "video"
        "data_url": data_url[:200] + "...",  # truncate for storage, real impl would store to file
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }
    session["captures"].append(capture)
    save_session(session)
    return {"capture_id": capture_id, "status": "saved"}


def session_to_room_state_actions(token: str) -> list[dict]:
    """
    Convert AR placements in a session into RoomState ADD actions
    that can be batch-applied to the main room state.
    """
    session = get_session(token)
    if not session:
        return []

    actions = []
    for p in session.get("ar_placements", []):
        actions.append({
            "action": "ADD",
            "params": {
                "type":       p.get("product_id", "sofa"),  # will be refined by product lookup
                "x":          p["x"],
                "z":          p["z"],
                "rotation":   p["rotation"],
                "ar_placed":  True,
                "ar_session": token,
            }
        })
    return actions


def generate_qr_code(token: str, base_url: str = "http://localhost:8000") -> dict:
    """
    Generate a QR code for cross-device session handoff.
    Returns {qr_url, qr_data_url} where qr_data_url is base64 PNG.
    """
    session_url = f"{base_url}/ar/session/{token}"

    try:
        import qrcode
        import io, base64
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(session_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        qr_data_url = f"data:image/png;base64,{b64}"
    except ImportError:
        # Fallback: return a Google Charts QR code URL
        import urllib.parse
        encoded = urllib.parse.quote(session_url)
        qr_data_url = f"https://chart.googleapis.com/chart?chs=300x300&cht=qr&chl={encoded}"

    return {
        "token":       token,
        "session_url": session_url,
        "qr_data_url": qr_data_url,
    }


def cleanup_expired_sessions():
    """Remove expired session files. Call periodically."""
    now = time.time()
    removed = 0
    for path in SESSION_DIR.glob("*.json"):
        try:
            session = json.loads(path.read_text())
            if now > session.get("expires_at", 0):
                path.unlink()
                removed += 1
        except Exception:
            pass
    if removed:
        log.info(f"Cleaned up {removed} expired AR sessions")

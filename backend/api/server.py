"""
FastAPI server — REST + WebSocket API for the AI Interior Designer.
Phase 2 & 3 additions:
  GET  /measurements   — inter-object distances & clearances
  GET  /budget         — cost estimation for placed furniture
  POST /versions/save  — snapshot current design
  GET  /versions       — list all snapshots
  GET  /versions/diff  — diff two snapshots
  DELETE /versions/{id} — delete snapshot
  POST /render         — AI photoreal image generation
  POST /import/blueprint — upload & parse floor plan
  GET  /products       — real product suggestions for a furniture type
"""
import os
import json
import asyncio
from contextlib import asynccontextmanager
from typing import Set, Optional
import math

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path)

from backend.state.state_manager import RoomState, default_state
from backend.graph.designer_graph import run_command
from backend.environment.objects import FURNITURE_CATALOG, get_furniture
from backend.storage.project_store import list_projects
from backend.storage.version_store import save_version, list_versions, load_version, diff_versions, delete_version
from backend.llm.image_renderer import render_image, build_render_prompt
from backend.blueprint_import.blueprint_parser import parse_blueprint
from backend.api.ikea_routes import router as ikea_router
from backend.catalog.product_search import get_product_by_id
from backend.actions.add import handle_add

# ─────────────────────── App-level state ────────────────────────────────────

_room_state: RoomState = default_state(
    room_width=float(os.getenv("ROOM_WIDTH", 10)),
    room_height=float(os.getenv("ROOM_HEIGHT", 8)),
)
_ws_clients: Set[WebSocket] = set()


async def _broadcast(state: RoomState):
    """Send updated state to all connected WebSocket clients."""
    if not _ws_clients:
        return
    payload = json.dumps({
        "type": "state_update",
        "state": _state_to_dict(state),
    })
    dead = set()
    for ws in _ws_clients:
        try:
            await ws.send_text(payload)
        except Exception:
            dead.add(ws)
    _ws_clients.difference_update(dead)


# ─────────────────────── FastAPI app ────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="AI Interior Designer API",
    version="2.0.0",
    description="Stateful AI room design system — Phase 2 & 3 features",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")


# ─────────────────────── Models ─────────────────────────────────────────────

class CommandRequest(BaseModel):
    command: str


class ResetRequest(BaseModel):
    width: float = 10.0
    height: float = 8.0


class SaveVersionRequest(BaseModel):
    name: str


class SelectionRequest(BaseModel):
    objectId: str


class PlaceProductRequest(BaseModel):
    productId: str
    x: Optional[float] = None
    z: Optional[float] = None


# ─────────────────────── Helper ─────────────────────────────────────────────

def _state_to_dict(state: RoomState) -> dict:
    return {
        "project": state.get("project", {}),
        "room": state.get("room", {}),
        "objects": state.get("objects", []),
        "history": state.get("history", []),
        "last_action": state.get("last_action", {}),
        "selected_object_id": state.get("selected_object_id", ""),
        "selected_product_id": state.get("selected_product_id", ""),
        "message": state.get("message", ""),
        "error": state.get("error"),
        "clearance_warnings": state.get("clearance_warnings", []),
        "accessibility_score": state.get("accessibility_score", 100),
    }


# ─────────────────────── Core Routes ────────────────────────────────────────

@app.get("/")
async def root():
    index_path = os.path.join(_FRONTEND_DIR, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path)
    return {"message": "AI Interior Designer API v2", "docs": "/docs"}


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "objects_in_room": len(_room_state.get("objects", [])),
        "accessibility_score": _room_state.get("accessibility_score", 100),
        "clearance_warnings": len(_room_state.get("clearance_warnings", [])),
    }


import urllib.request
import urllib.error
import re


@app.get("/llm-status")
def llm_status():
    """Verify if the OpenRouter API key is valid synchronously."""
    url = "https://openrouter.ai/api/v1/auth/key"
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {os.getenv('OPENROUTER_API_KEY', '')}")
    try:
        with urllib.request.urlopen(req, timeout=5) as res:
            data = json.loads(res.read().decode())
        return {"connected": True, "model": os.getenv("OPENROUTER_MODEL"), "key_info": data}
    except urllib.error.HTTPError as e:
        status_msg = "Invalid API Key" if e.code in (401, 403) else f"HTTP {e.code}"
        return {"connected": False, "model": os.getenv("OPENROUTER_MODEL"), "error": status_msg}
    except Exception as e:
        return {"connected": False, "model": os.getenv("OPENROUTER_MODEL"), "error": str(e)}


@app.get("/state")
async def get_state():
    return _state_to_dict(_room_state)


@app.get("/img")
async def proxy_image(u: str = Query(..., description="Remote image URL to proxy")):
    """
    Proxy remote product images through this backend to avoid hotlink/CORS issues.
    Only allows ikea.com image hosts by default.
    """
    import httpx
    from urllib.parse import urlparse

    url = (u or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="Missing url")

    # Basic allowlist: only ikea.com and ikea CDN images
    if not re.search(r"^https?://([^/]+\.)?ikea\.com/", url, flags=re.IGNORECASE):
        raise HTTPException(status_code=400, detail="Unsupported image host")

    # Try to make Referer match the requested locale (some IKEA endpoints are picky)
    parsed = urlparse(url)
    path_parts = [p for p in (parsed.path or "").split("/") if p]
    referer = "https://www.ikea.com/"
    if len(path_parts) >= 2:
        cc, lang = path_parts[0].lower(), path_parts[1].lower()
        if re.fullmatch(r"[a-z]{2}", cc) and re.fullmatch(r"[a-z]{2}", lang):
            referer = f"{parsed.scheme}://{parsed.netloc}/{cc}/{lang}/"

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": referer,
    }
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
            r = await client.get(url, headers=headers)
            if r.status_code != 200 or not r.content:
                raise HTTPException(status_code=404, detail=f"Image fetch failed: HTTP {r.status_code}")
            ctype = r.headers.get("content-type", "image/jpeg")
            return StreamingResponse(
                iter([r.content]),
                media_type=ctype,
                headers={
                    "Cache-Control": "public, max-age=86400",
                },
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Image proxy error: {str(e)}")


@app.get("/catalog")
async def get_catalog():
    return FURNITURE_CATALOG


@app.get("/projects")
async def get_projects():
    return {"projects": list_projects()}


@app.post("/command")
async def post_command(req: CommandRequest):
    global _room_state
    if not req.command.strip():
        raise HTTPException(status_code=400, detail="Command cannot be empty")
    try:
        new_state = await asyncio.to_thread(run_command, req.command.strip(), _room_state)
        _room_state = new_state
        await _broadcast(_room_state)
        return {
            "success": True,
            "message": new_state.get("message", ""),
            "state": _state_to_dict(new_state),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Command processing failed: {str(e)}")


@app.post("/reset")
async def reset_room(req: ResetRequest = ResetRequest()):
    global _room_state
    _room_state = default_state(req.width, req.height)
    await _broadcast(_room_state)
    return {"success": True, "message": "Room has been reset.", "state": _state_to_dict(_room_state)}


@app.post("/select")
async def select_object(req: SelectionRequest):
    global _room_state
    _room_state = {
        **_room_state,
        "selected_object_id": req.objectId,
        "last_action": {"type": "SELECT_OBJECT", "object_id": req.objectId},
        "message": f"🎯 Selected {req.objectId}.",
        "error": None,
    }
    await _broadcast(_room_state)
    return {"success": True, "state": _state_to_dict(_room_state)}


@app.post("/products/place")
async def place_product(req: PlaceProductRequest):
    global _room_state
    product = get_product_by_id(req.productId)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product not found: {req.productId}")

    def _to_float(v, default=None):
        try:
            if v is None:
                return default
            return float(v)
        except Exception:
            return default

    def _dim_m(p: dict, cm_key: str, m_key: str, fallback_m: float) -> float:
        cm = _to_float(p.get(cm_key))
        if cm and cm > 0:
            return cm / 100.0
        m = _to_float(p.get(m_key))
        if m and m > 0:
            return m
        return fallback_m

    width_m = _dim_m(product, "width_cm", "width", 1.0)
    depth_m = _dim_m(product, "depth_cm", "depth", 0.6)
    height_m = _dim_m(product, "height_cm", "height", 0.8)
    object_type = str(product.get("category", "furniture")).lower().replace(" ", "_")
    product_id = str(product.get("id") or product.get("item_no") or req.productId)
    price = product.get("price_usd")
    if price is None:
        price = product.get("price_low")
    if price is None:
        price = product.get("price")
    price = _to_float(price, None)

    _room_state = handle_add(
        _room_state,
        {
            "object": object_type,
            "constraints": {"placement": "auto"},
            "x": req.x,
            "z": req.z,
            "source": "ikea",
            "product_id": product_id,
            "product_name": product.get("name"),
            "image_url": product.get("image_url"),
            "price": price,
            "brand": product.get("brand", "IKEA"),
            "custom_definition": {
                "size": [width_m, depth_m],
                "height": max(0.3, height_m),
                "description": product.get("name", object_type.replace("_", " ").title()),
                "color": "#9aa0a6",
            },
        },
    )
    if _room_state.get("error"):
        raise HTTPException(status_code=400, detail=_room_state["error"])
    await _broadcast(_room_state)
    return {"success": True, "state": _state_to_dict(_room_state)}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    _ws_clients.add(websocket)
    try:
        await websocket.send_text(json.dumps({
            "type": "state_update",
            "state": _state_to_dict(_room_state),
        }))
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "command":
                    await post_command(CommandRequest(command=msg.get("command", "")))
            except Exception:
                pass
    except WebSocketDisconnect:
        _ws_clients.discard(websocket)


# ─────────────────────── Phase 2: Measurements ──────────────────────────────

@app.get("/measurements")
async def get_measurements():
    """Return inter-object distances, room clearances, and walkability info."""
    objects = _room_state.get("objects", [])
    room = _room_state.get("room", {})
    rw = room.get("width", 10)
    rh = room.get("height", 8)
    margin = room.get("wall_thickness", 0.2)

    distances = []
    for i, a in enumerate(objects):
        for j, b in enumerate(objects):
            if j <= i:
                continue
            ax1, az1 = a["x"], a["z"]
            ax2, az2 = ax1 + a["w"], az1 + a["d"]
            bx1, bz1 = b["x"], b["z"]
            bx2, bz2 = bx1 + b["w"], bz1 + b["d"]
            gap_x = max(ax1 - bx2, bx1 - ax2, 0)
            gap_z = max(az1 - bz2, bz1 - az2, 0)
            gap = round(math.sqrt(gap_x ** 2 + gap_z ** 2), 2)
            distances.append({
                "id_a": a["id"], "type_a": a.get("type"),
                "id_b": b["id"], "type_b": b.get("type"),
                "gap_m": gap,
                "sufficient": gap >= 0.6,
            })

    # Wall clearances per object
    clearances = []
    for obj in objects:
        clearances.append({
            "id": obj["id"],
            "type": obj.get("type"),
            "wall_gaps": {
                "west":  round(obj["x"] - margin, 2),
                "east":  round(rw - margin - (obj["x"] + obj["w"]), 2),
                "north": round(obj["z"] - margin, 2),
                "south": round(rh - margin - (obj["z"] + obj["d"]), 2),
            },
        })

    return {
        "room": {"width": rw, "height": rh},
        "inter_object_distances": distances,
        "wall_clearances": clearances,
        "clearance_warnings": _room_state.get("clearance_warnings", []),
        "accessibility_score": _room_state.get("accessibility_score", 100),
    }


# ─────────────────────── Phase 2: Budget ────────────────────────────────────

@app.get("/budget")
async def get_budget():
    """Estimate cost range for all furniture in the current room."""
    objects = _room_state.get("objects", [])
    items = []
    total_low = 0
    total_high = 0

    for obj in objects:
        cat = get_furniture(obj.get("type", "")) or {}
        low = cat.get("price_low", 0)
        high = cat.get("price_high", 0)
        total_low += low
        total_high += high
        items.append({
            "id": obj["id"],
            "type": obj.get("type"),
            "description": cat.get("description", obj.get("type")),
            "price_low": low,
            "price_high": high,
            "category": cat.get("category", "general"),
        })

    return {
        "items": items,
        "total_low": total_low,
        "total_high": total_high,
        "currency": "USD",
        "note": "Price ranges are estimates based on typical market prices.",
    }


# ─────────────────────── Phase 2: Version Comparison ───────────────────────

@app.post("/versions/save")
async def save_design_version(req: SaveVersionRequest):
    """Save current design as a named snapshot."""
    snapshot = save_version(req.name, _state_to_dict(_room_state))
    return {"success": True, "version": snapshot}


@app.get("/versions")
async def get_versions():
    """List all saved design snapshots."""
    return {"versions": list_versions()}


@app.get("/versions/diff")
async def get_version_diff(a: str = Query(..., description="First version ID"), b: str = Query(..., description="Second version ID")):
    """Compute a diff between two named design versions."""
    result = diff_versions(a, b)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.get("/versions/{version_id}")
async def get_version(version_id: str):
    """Load a specific version snapshot."""
    v = load_version(version_id)
    if v is None:
        raise HTTPException(status_code=404, detail=f"Version '{version_id}' not found")
    return v


@app.delete("/versions/{version_id}")
async def delete_design_version(version_id: str):
    """Delete a version snapshot."""
    deleted = delete_version(version_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Version '{version_id}' not found")
    return {"success": True, "deleted": version_id}


# ─────────────────────── Phase 3: AI Photoreal Rendering ───────────────────

@app.post("/render")
async def render_room():
    """Generate a photorealistic AI render of the current room."""
    try:
        result = await asyncio.to_thread(render_image, _state_to_dict(_room_state))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Render failed: {str(e)}")


@app.get("/render/prompt")
async def get_render_prompt():
    """Preview the prompt that would be sent to the image generation API."""
    prompt = build_render_prompt(_state_to_dict(_room_state))
    return {"prompt": prompt}


# ─────────────────────── Phase 3: Blueprint Import ──────────────────────────

@app.post("/import/blueprint")
async def import_blueprint(file: UploadFile = File(...)):
    """
    Upload a floor plan image (PNG/JPG) and extract room data from it.
    Returns a partial room state dict to apply to the current room.
    """
    allowed = {".png", ".jpg", ".jpeg", ".webp"}
    ext = os.path.splitext(file.filename or "")[-1].lower()
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}. Use PNG or JPG.")

    image_bytes = await file.read()
    if len(image_bytes) > 10 * 1024 * 1024:  # 10 MB limit
        raise HTTPException(status_code=400, detail="File too large (max 10 MB)")

    try:
        parsed = await asyncio.to_thread(parse_blueprint, image_bytes, file.filename or "upload.png")
        return {"success": True, "parsed": parsed}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Blueprint parsing failed: {str(e)}")


# ─────────────────────── Phase 3: IKEA Product Catalogs ───────────────────

# Mount the heavy-duty IKEA database queries and backend scrapers
app.include_router(ikea_router, prefix="")


# ─────────────────────── Static files ───────────────────────────────────────

if os.path.isdir(_FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=_FRONTEND_DIR), name="static")


# ─────────────────────── Entry point ────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.api.server:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        reload=True,
    )

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
Phase 4A/4B/4D additions:
  POST /scan/frame     — live camera frame → LLM vision room scan
  GET  /score          — 5-dimension layout score
  GET  /zones          — functional zone detection
  POST /goal           — set design goal, generate action plan
  POST /simulate       — what-if simulation (no state mutation)
  POST /autofix        — auto-fix layout issues
  GET  /preference/{session_id}  — preference profile
  POST /preference/{session_id}/signal — record preference signal
  POST /ar/session     — create AR session
  GET  /ar/session/{token} — get AR session
  POST /ar/session/{token}/place — place product in AR
  POST /ar/session/{token}/capture — save AR screenshot
  GET  /ar/session/{token}/qr — get QR code for cross-device handoff
  POST /ar/session/{token}/save-to-design — commit AR→RoomState
  GET  /ar/product/{item_id}/preview — product AR preview with EGP price
  GET  /products/catalog — IKEA Egypt product catalog (EGP)
"""
import os
import json
import asyncio
from contextlib import asynccontextmanager
from typing import Set, Optional
import math

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File, Query, Request
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
from backend.catalog.multi_retailer import search_multi_retailer
from backend.catalog.sustainability_scorer import sustainability_score
from backend.actions.add import handle_add

# Phase 4B — Layout intelligence
from backend.engine.layout_scorer import score_layout
from backend.engine.zoning import detect_zones
from backend.planner.goal_planner import plan_goal
from backend.planner.what_if_engine import simulate
from backend.planner.preference_store import record_signal, get_preference_summary
from backend.collab.share_manager import create_share, load_share
from backend.collab.comment_store import add_comment, list_comments, update_comment, delete_comment
from backend.export.material_takeoff import compute_takeoff
from backend.export.dxf_exporter import export_room_dxf
from backend.storage.home_store import load_home, save_home
from backend.storage.tenant_store import resolve_tenant
from backend.auth.auth_manager import register_user, authenticate_user, create_token, verify_token, list_users_by_tenant
from backend.storage.migrations import migrate_comments_default_tenant
from backend.storage.render_jobs import create_render_job, get_render_job

# Phase 4A + 4D — AR & vision
from backend.vision.live_scanner import scan_frame
from backend.ar.session_manager import (
    create_session, get_session, save_session,
    place_product as ar_place_product,
    save_capture as ar_save_capture,
    generate_qr_code,
    session_to_room_state_actions,
)

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
    # one-time compatibility migrations (safe/idempotent)
    try:
      migrate_comments_default_tenant()
    except Exception:
      pass
    yield


app = FastAPI(
    title="AI Interior Designer API",
    version="4.0.0",
    description="Stateful AI room design — Phases 2–4D: Egypt IKEA catalog, AR, scoring, goal planning",
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
    command: str = ""
    action: str = ""
    params: dict = {}


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


class GoalRequest(BaseModel):
    goal: str
    session_id: str = "default"


class SimulateRequest(BaseModel):
    actions: list


class ScanFrameRequest(BaseModel):
    image: str          # base64 JPEG/PNG
    format: str = "jpeg"


class ARPlaceRequest(BaseModel):
    product_id: str
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    rotation: float = 0.0
    scale: float = 1.0


class ARCaptureRequest(BaseModel):
    type: str = "photo"   # "photo" or "video"
    data_url: str = ""


class PreferenceSignalRequest(BaseModel):
    signal_type: str
    value: str

class ApplyActionsRequest(BaseModel):
    actions: list = []

class VoiceCommandRequest(BaseModel):
    text: str = ""
    session_id: str = "default"

class SketchImportRequest(BaseModel):
    image: str = ""   # dataURL or base64 payload

class RetailerSearchResponse(BaseModel):
    products: list = []

class ShareRequest(BaseModel):
    role: str = "view"
    ttl_seconds: int = 7 * 24 * 3600

class CommentRequest(BaseModel):
    text: str = ""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    object_id: str = ""

class CommentUpdateRequest(BaseModel):
    text: str = ""

class HomeAddRoomRequest(BaseModel):
    room_id: str = ""
    name: str = ""

class HomeConnectRequest(BaseModel):
    a: str
    b: str
    type: str = "door"

class AuthRegisterRequest(BaseModel):
    email: str
    password: str
    name: str = ""

class AuthLoginRequest(BaseModel):
    email: str
    password: str

class RenderVideoRequest(BaseModel):
    duration_sec: int = 10
    quality: str = "standard"


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

def _summarize_actions(actions: list) -> dict:
    """Lightweight summary for preview UIs."""
    counts: dict[str, int] = {}
    for a in (actions or []):
        t = str(a.get("action") or a.get("type") or "").upper() or "UNKNOWN"
        counts[t] = counts.get(t, 0) + 1
    return {"total_actions": sum(counts.values()), "by_type": counts}

async def _apply_actions(actions: list) -> int:
    """Apply a list of {action, params} to the global RoomState."""
    global _room_state
    applied = 0
    for a in (actions or []):
        action = (a.get("action") or a.get("type") or "").strip().upper()
        params = a.get("params") or {}
        if not action:
            continue
        command = f"{action} {json.dumps(params)}"
        try:
            new_state = await asyncio.to_thread(run_command, command, _room_state)
            _room_state = new_state
            applied += 1
        except Exception:
            # best-effort apply; failures are ignored so partial scans can still help
            pass
    if applied:
        await _broadcast(_room_state)
    return applied


def _tenant_id_from_request(request: Request) -> str:
    host = request.headers.get("host", "")
    return str(resolve_tenant(host).get("id") or "default")


def _user_from_request(request: Request) -> dict | None:
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        return None
    token = auth.split(" ", 1)[1].strip()
    payload = verify_token(token)
    return payload


def _require_auth(request: Request) -> dict:
    u = _user_from_request(request)
    if not u:
        raise HTTPException(status_code=401, detail="Authentication required")
    tenant_id = _tenant_id_from_request(request)
    if str(u.get("tenant_id") or "") != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    return u


def _require_role(request: Request, allowed: set[str]) -> dict:
    u = _require_auth(request)
    role = str(u.get("role") or "viewer")
    if role not in allowed:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return u


def _feature_enabled(request: Request, feature_key: str) -> bool:
    host = request.headers.get("host", "")
    t = resolve_tenant(host)
    flags = t.get("feature_flags", {}) or {}
    return bool(flags.get(feature_key, True))


def _require_feature(request: Request, feature_key: str):
    if not _feature_enabled(request, feature_key):
        raise HTTPException(status_code=403, detail=f"Service '{feature_key}' disabled for this tenant")


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

@app.get("/tenant/config")
async def tenant_config(request: Request):
    """
    Phase 6.0 MVP: resolve tenant by host and return branding + feature flags.
    """
    host = request.headers.get("host", "")
    t = resolve_tenant(host)
    return {
        "id": t.get("id"),
        "name": t.get("name"),
        "branding": t.get("branding", {}),
        "feature_flags": t.get("feature_flags", {}),
    }


@app.get("/tenant/services")
async def tenant_services(request: Request):
    """
    Phase 6.0 MVP: service catalog per tenant/site.
    """
    host = request.headers.get("host", "")
    t = resolve_tenant(host)
    services = t.get("services", [])
    return {"tenant_id": t.get("id"), "services": services}


# ─────────────────────── Phase 6.1: Auth (MVP) ──────────────────────────────

@app.post("/auth/register")
async def auth_register(req: AuthRegisterRequest, request: Request):
    tenant_id = _tenant_id_from_request(request)
    try:
        # First tenant user becomes owner, subsequent users default to viewer.
        existing = list_users_by_tenant(tenant_id)
        role = "owner" if len(existing) == 0 else "viewer"
        user = register_user(req.email, req.password, tenant_id=tenant_id, name=req.name or "", role=role)
        token = create_token(user)
        return {"user": user, "access_token": token, "token_type": "bearer"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/auth/login")
async def auth_login(req: AuthLoginRequest, request: Request):
    tenant_id = _tenant_id_from_request(request)
    user = authenticate_user(req.email, req.password, tenant_id=tenant_id)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(user)
    return {"user": user, "access_token": token, "token_type": "bearer"}


@app.get("/auth/me")
async def auth_me(request: Request):
    u = _user_from_request(request)
    if not u:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"user": {"id": u.get("sub"), "email": u.get("email"), "name": u.get("name"), "tenant_id": u.get("tenant_id")}}


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

@app.get("/model")
async def proxy_model(u: str = Query(..., description="Remote GLB/GLTF URL to proxy")):
    """
    Proxy remote 3D models (GLB/GLTF) through this backend to avoid CORS/hotlink issues.
    Basic allowlist: ikea.com + asset.inter.ikea.com.
    """
    import httpx
    from urllib.parse import urlparse

    url = (u or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="Missing url")

    # Allowlist IKEA hosts (site + asset CDN)
    if not re.search(r"^https?://([^/]+\.)?ikea\.com/", url, flags=re.IGNORECASE) and not re.search(
        r"^https?://asset\.inter\.ikea\.com/", url, flags=re.IGNORECASE
    ):
        raise HTTPException(status_code=400, detail="Unsupported model host")

    # Only allow model-like extensions
    p = urlparse(url)
    ext = os.path.splitext(p.path or "")[-1].lower()
    if ext not in (".glb", ".gltf"):
        raise HTTPException(status_code=400, detail="Only .glb/.gltf models are supported")

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.ikea.com/",
    }
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
            r = await client.get(url, headers=headers)
            if r.status_code != 200 or not r.content:
                raise HTTPException(status_code=404, detail=f"Model fetch failed: HTTP {r.status_code}")
            ctype = r.headers.get("content-type") or ("model/gltf-binary" if ext == ".glb" else "model/gltf+json")
            return StreamingResponse(
                iter([r.content]),
                media_type=ctype,
                headers={"Cache-Control": "public, max-age=86400"},
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Model proxy error: {str(e)}")


@app.get("/catalog")
async def get_catalog():
    return FURNITURE_CATALOG


# ─────────────────────── Phase 5.2: Multi-Retailer Commerce ──────────────────

@app.get("/products/search")
async def products_search_multi(
    request: Request,
    q: str = Query(default="", description="Search query"),
    budget: float = Query(default=0, ge=0, description="Max price"),
    style: str = Query(default="", description="Style hint (optional)"),
    retailers: str = Query(default="ikea", description="Comma-separated retailers: ikea,wayfair,amazon,west_elm"),
    limit: int = Query(default=50, ge=1, le=200),
):
    _require_feature(request, "commerce")
    _require_auth(request)
    """
    Phase 5.2 MVP: Unified search across retailers.
    Currently returns IKEA results; other retailers are stubs until integrated.
    """
    ret_list = [r.strip() for r in (retailers or "").split(",") if r.strip()]
    products = search_multi_retailer(query=q, style=style, budget=budget, retailers=ret_list, limit=limit)
    return {"products": products, "count": len(products), "retailers": ret_list}


@app.get("/products/availability")
async def products_availability(
    request: Request,
    ids: str = Query(default="", description="Comma-separated product IDs"),
    retailer: str = Query(default="ikea", description="Retailer name"),
):
    _require_feature(request, "commerce")
    _require_auth(request)
    """
    Phase 5.2 MVP: Availability checker.
    For IKEA, uses cached in_stock where available; otherwise returns unknown.
    """
    retailer = (retailer or "ikea").strip().lower()
    id_list = [i.strip() for i in (ids or "").split(",") if i.strip()]
    out = []
    for pid in id_list[:200]:
        p = get_product_by_id(pid) if retailer == "ikea" else None
        out.append({
            "id": pid,
            "retailer": retailer,
            "in_stock": (p.get("in_stock") if isinstance(p, dict) else None),
        })
    return {"items": out, "count": len(out)}


@app.get("/products/bundle")
async def products_bundle(request: Request):
    _require_feature(request, "commerce")
    _require_auth(request)
    """
    Phase 5.2 MVP: Bundle suggestions for current room.
    Returns simple category-based recommendations using IKEA catalog.
    """
    objects = _room_state.get("objects", []) or []
    want = []
    if any(o.get("type") in ("sofa", "armchair", "sectional_sofa") for o in objects):
        want += ["coffee_table", "rug", "lamp"]
    if any(o.get("type") in ("bed", "single_bed") for o in objects):
        want += ["nightstand", "lamp", "wardrobe"]
    if any(o.get("type") in ("desk",) for o in objects):
        want += ["office_chair", "bookshelf", "lamp"]

    # De-dupe while preserving order
    seen = set()
    want = [w for w in want if not (w in seen or seen.add(w))]

    bundles = []
    for cat in want[:6]:
        rows = search_multi_retailer(query=cat.replace("_", " "), budget=0, retailers=["ikea"], limit=6)
        bundles.append({"category": cat, "products": rows})
    return {"bundles": bundles, "count": len(bundles)}


@app.get("/products/sustainability/{product_id}")
async def product_sustainability(product_id: str, request: Request):
    _require_feature(request, "commerce")
    _require_auth(request)
    """
    Phase 5.2 MVP: Sustainability score for a product (heuristic).
    """
    p = get_product_by_id(product_id)
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"product_id": product_id, **sustainability_score(p)}


@app.get("/projects")
async def get_projects():
    return {"projects": list_projects()}


# ─────────────────────── Phase 5.5: Share / Comments / Export ────────────────

@app.post("/share")
async def share_link(req: ShareRequest, request: Request):
    _require_feature(request, "collab")
    _require_role(request, {"owner", "admin", "editor"})
    tenant_id = _tenant_id_from_request(request)
    payload = create_share(_state_to_dict(_room_state), role=req.role, tenant_id=tenant_id, ttl_seconds=req.ttl_seconds)
    return payload


@app.get("/share/{token}")
async def share_load(token: str, request: Request):
    _require_feature(request, "collab")
    _require_auth(request)
    tenant_id = _tenant_id_from_request(request)
    row = load_share(token, tenant_id=tenant_id)
    if not row:
        raise HTTPException(status_code=404, detail="Share token not found")
    return row


@app.post("/comments")
async def comments_add(req: CommentRequest, request: Request):
    _require_feature(request, "collab")
    _require_role(request, {"owner", "admin", "editor"})
    if not (req.text or "").strip():
        raise HTTPException(status_code=400, detail="text cannot be empty")
    tenant_id = _tenant_id_from_request(request)
    row = add_comment(req.text.strip(), req.x, req.y, req.z, object_id=req.object_id or "", tenant_id=tenant_id)
    return {"success": True, "comment": row}


@app.get("/comments")
async def comments_list(request: Request):
    _require_feature(request, "collab")
    _require_auth(request)
    tenant_id = _tenant_id_from_request(request)
    items = list_comments(tenant_id=tenant_id)
    return {"comments": items, "count": len(items)}


@app.put("/comments/{comment_id}")
async def comments_update(comment_id: str, req: CommentUpdateRequest, request: Request):
    _require_feature(request, "collab")
    _require_role(request, {"owner", "admin", "editor"})
    tenant_id = _tenant_id_from_request(request)
    row = update_comment(comment_id, req.text.strip(), tenant_id=tenant_id)
    if not row:
        raise HTTPException(status_code=404, detail="Comment not found")
    return {"success": True, "comment": row}


@app.delete("/comments/{comment_id}")
async def comments_delete(comment_id: str, request: Request):
    _require_feature(request, "collab")
    _require_role(request, {"owner", "admin", "editor"})
    tenant_id = _tenant_id_from_request(request)
    ok = delete_comment(comment_id, tenant_id=tenant_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Comment not found")
    return {"success": True, "deleted": comment_id}


@app.post("/export/pdf")
async def export_pdf():
    """
    MVP: return a payload the frontend can turn into a PDF (client-side jsPDF).
    """
    return {
        "success": True,
        "format": "pdf",
        "state": _state_to_dict(_room_state),
        "note": "MVP: generate the actual PDF client-side from this payload.",
    }


@app.post("/export/dxf")
async def export_dxf():
    """
    Return DXF text for simple CAD import.
    """
    dxf = export_room_dxf(_state_to_dict(_room_state))
    return StreamingResponse(
        iter([dxf.encode("utf-8")]),
        media_type="application/dxf",
        headers={"Content-Disposition": "attachment; filename=room.dxf"},
    )


@app.get("/export/materials")
async def export_materials():
    return compute_takeoff(_state_to_dict(_room_state))


# ─────────────────────── Phase 5.6: Multi-room (MVP) ─────────────────────────

@app.post("/home/rooms")
async def home_add_room(req: HomeAddRoomRequest, request: Request):
    _require_feature(request, "home")
    _require_role(request, {"owner", "admin", "editor"})
    tenant_id = _tenant_id_from_request(request)
    home = load_home(tenant_id=tenant_id)
    rid = (req.room_id or "").strip() or f"room_{len(home.get('rooms', {})) + 1}"
    rooms = home.get("rooms", {}) or {}
    rooms[rid] = {
        "id": rid,
        "name": req.name or rid,
        "state": _state_to_dict(_room_state),
    }
    home["rooms"] = rooms
    save_home(home, tenant_id=tenant_id)
    return {"success": True, "home": home}


@app.post("/home/connect")
async def home_connect(req: HomeConnectRequest, request: Request):
    _require_feature(request, "home")
    _require_role(request, {"owner", "admin", "editor"})
    tenant_id = _tenant_id_from_request(request)
    home = load_home(tenant_id=tenant_id)
    rooms = home.get("rooms", {}) or {}
    if req.a not in rooms or req.b not in rooms:
        raise HTTPException(status_code=400, detail="Both rooms must exist")
    if req.a == req.b:
        raise HTTPException(status_code=400, detail="Cannot connect room to itself")
    conns = home.get("connections", []) or []
    if any((c.get("a") == req.a and c.get("b") == req.b) or (c.get("a") == req.b and c.get("b") == req.a) for c in conns):
        raise HTTPException(status_code=400, detail="Connection already exists")
    conns.append({"a": req.a, "b": req.b, "type": req.type})
    home["connections"] = conns
    save_home(home, tenant_id=tenant_id)
    return {"success": True, "home": home}


@app.get("/home/budget")
async def home_budget(request: Request):
    _require_feature(request, "home")
    _require_auth(request)
    tenant_id = _tenant_id_from_request(request)
    home = load_home(tenant_id=tenant_id)
    total_low = 0.0
    total_high = 0.0
    per_room = []
    for rid, r in (home.get("rooms", {}) or {}).items():
        state = (r or {}).get("state") or {}
        # Reuse existing /budget logic quickly by summing catalog ranges
        low = 0.0
        high = 0.0
        for obj in state.get("objects", []) or []:
            cat = get_furniture(obj.get("type", "")) or {}
            low += float(cat.get("price_low", 0) or 0)
            high += float(cat.get("price_high", 0) or 0)
        total_low += low
        total_high += high
        per_room.append({"room_id": rid, "low": low, "high": high})
    return {"total_low": total_low, "total_high": total_high, "rooms": per_room, "currency": "USD"}


@app.get("/home/flow")
async def home_flow(request: Request):
    _require_feature(request, "home")
    _require_auth(request)
    """
    MVP traffic flow: return graph stats from connections.
    """
    tenant_id = _tenant_id_from_request(request)
    home = load_home(tenant_id=tenant_id)
    conns = home.get("connections", []) or []
    rooms = list((home.get("rooms", {}) or {}).keys())
    degree = {r: 0 for r in rooms}
    for c in conns:
        a = c.get("a"); b = c.get("b")
        if a in degree: degree[a] += 1
        if b in degree: degree[b] += 1
    hotspots = sorted(degree.items(), key=lambda kv: kv[1], reverse=True)[:5]
    # connected components
    graph = {r: set() for r in rooms}
    for c in conns:
        a, b = c.get("a"), c.get("b")
        if a in graph and b in graph:
            graph[a].add(b)
            graph[b].add(a)
    visited = set()
    components = []
    for r in rooms:
        if r in visited:
            continue
        stack = [r]
        comp = []
        while stack:
            n = stack.pop()
            if n in visited:
                continue
            visited.add(n)
            comp.append(n)
            stack.extend(graph.get(n, []))
        components.append(comp)
    return {
        "rooms": rooms,
        "connections": conns,
        "degree": degree,
        "hotspots": hotspots,
        "components": components,
        "is_fully_connected": len(components) <= 1,
    }


@app.post("/command")
async def post_command(req: CommandRequest, request: Request):
    _require_role(request, {"owner", "admin", "editor"})
    global _room_state
    # Support both text commands and structured action/params
    if req.action:
        command_str = f"{req.action} {json.dumps(req.params)}"
    elif req.command.strip():
        command_str = req.command.strip()
    else:
        raise HTTPException(status_code=400, detail="Command cannot be empty")
    try:
        new_state = await asyncio.to_thread(run_command, command_str, _room_state)
        _room_state = new_state
        await _broadcast(_room_state)
        return {
            "success": True,
            "message": new_state.get("message", ""),
            "state": _state_to_dict(new_state),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Command processing failed: {str(e)}")

@app.post("/voice/command")
async def voice_command(req: VoiceCommandRequest, request: Request):
    _require_feature(request, "voice")
    _require_role(request, {"owner", "admin", "editor"})
    """
    Phase 5.3 (v1): Accept already-transcribed text and execute it like /command.
    (Audio/STT stays planned.)
    """
    global _room_state
    text = (req.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text cannot be empty")
    try:
        new_state = await asyncio.to_thread(run_command, text, _room_state)
        _room_state = new_state
        record_signal(req.session_id, "voice_command", text)
        await _broadcast(_room_state)
        return {"success": True, "message": new_state.get("message", ""), "state": _state_to_dict(new_state)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voice command failed: {str(e)}")


@app.post("/reset")
async def reset_room(request: Request, req: ResetRequest = ResetRequest()):
    _require_role(request, {"owner", "admin", "editor"})
    global _room_state
    _room_state = default_state(req.width, req.height)
    await _broadcast(_room_state)
    return {"success": True, "message": "Room has been reset.", "state": _state_to_dict(_room_state)}


@app.post("/select")
async def select_object(req: SelectionRequest, request: Request):
    _require_auth(request)
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
async def place_product(req: PlaceProductRequest, request: Request):
    _require_feature(request, "catalog")
    _require_role(request, {"owner", "admin", "editor"})
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
    model_url = product.get("model_url") or ""
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
            "model_url": model_url,
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
                    command_text = str(msg.get("command", "")).strip()
                    if command_text:
                        new_state = await asyncio.to_thread(run_command, command_text, _room_state)
                        globals()["_room_state"] = new_state
                        await _broadcast(_room_state)
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

@app.post("/render/video")
async def render_video(req: RenderVideoRequest, request: Request):
    """
    Phase 5.4: enqueue a render video job and return job metadata.
    Server-side renderer remains queued (client-side recording fallback available).
    """
    _require_auth(request)
    job = create_render_job({"duration_sec": req.duration_sec, "quality": req.quality})
    return {"success": True, "job": job}


@app.get("/render/video/{job_id}")
async def render_video_status(job_id: str, request: Request):
    _require_auth(request)
    row = get_render_job(job_id)
    if not row:
        raise HTTPException(status_code=404, detail="Render job not found")
    return row


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

@app.post("/import/photo/preview")
async def import_photo_preview(file: UploadFile = File(...)):
    """
    Phase 5.1: Upload a real room photo and return a preview (no state mutation).
    Returns scan JSON + ready-to-apply RoomState actions.
    """
    allowed = {".png", ".jpg", ".jpeg", ".webp"}
    ext = os.path.splitext(file.filename or "")[-1].lower()
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}. Use PNG or JPG.")

    image_bytes = await file.read()
    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 10 MB)")

    import base64
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    result = await asyncio.to_thread(scan_frame, b64, None, "", False)
    actions = result.get("actions") or []
    return {
        "success": True,
        "scan": result,
        "actions": actions,
        "summary": _summarize_actions(actions),
    }

@app.post("/import/photo")
async def import_photo(file: UploadFile = File(...)):
    """
    Phase 5.1: Upload a real room photo and apply extracted actions to RoomState.
    """
    preview = await import_photo_preview(file)
    actions = preview.get("actions") or []
    applied = await _apply_actions(actions)
    return {
        "success": True,
        "actions_applied": applied,
        "summary": preview.get("summary"),
        "state": _state_to_dict(_room_state),
        "scan": preview.get("scan"),
    }

@app.post("/style/detect")
async def style_detect(file: UploadFile | None = File(default=None)):
    """
    Phase 5.1: Detect aesthetic style from a photo or (fallback) from current RoomState.
    """
    if file is not None:
        allowed = {".png", ".jpg", ".jpeg", ".webp"}
        ext = os.path.splitext(file.filename or "")[-1].lower()
        if ext not in allowed:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}. Use PNG or JPG.")
        image_bytes = await file.read()
        if len(image_bytes) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large (max 10 MB)")
        import base64
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        result = await asyncio.to_thread(scan_frame, b64, None, "", False)
        return {
            "style": result.get("style") or "unknown",
            "confidence": float(result.get("confidence") or 0.0),
            "notes": result.get("notes") or "",
        }

    # Fallback heuristic from current state (best-effort)
    room = _room_state.get("room", {}) or {}
    theme = room.get("theme") or ""
    wall = (room.get("wall_style") or {}).get("material") or ""
    floor = (room.get("floor_style") or {}).get("material") or ""
    objs = _room_state.get("objects", []) or []
    types = {str(o.get("type") or "") for o in objs}

    style = (str(theme).strip() or "modern").lower()
    notes = []
    if "wood" in str(floor).lower():
        notes.append("wood flooring")
    if "marble" in str(floor).lower() or "stone" in str(floor).lower():
        notes.append("stone-like flooring")
    if "brick" in str(wall).lower() or "concrete" in str(wall).lower():
        style = "industrial"
        notes.append("industrial wall finish")
    if {"plant", "rug"} & {t for t in types if t}:
        notes.append("soft accents present")
    return {"style": style, "confidence": 0.35, "notes": ", ".join(notes)}

@app.post("/import/sketch")
async def import_sketch(req: SketchImportRequest, apply: int = Query(default=0, ge=0, le=1)):
    """
    Phase 5.3 (v1): Import a hand-drawn sketch (PNG dataURL/base64) using vision scan.
    - apply=0: preview only
    - apply=1: apply extracted actions to RoomState
    """
    img = (req.image or "").strip()
    if not img:
        raise HTTPException(status_code=400, detail="image cannot be empty")

    # scan_frame accepts base64; it also strips 'base64,' prefix if present.
    result = await asyncio.to_thread(scan_frame, img, None, "", False)
    actions = result.get("actions") or []
    applied = 0
    if apply:
        applied = await _apply_actions(actions)
    return {
        "success": True,
        "scan": result,
        "actions": actions,
        "actions_applied": applied,
        "summary": _summarize_actions(actions),
        "state": _state_to_dict(_room_state) if apply else None,
    }


# ─────────────────────── Phase 3: IKEA Product Catalogs ───────────────────

# Mount the heavy-duty IKEA database queries and backend scrapers
app.include_router(ikea_router, prefix="")


# ─── Phase 4A: Camera Scan ───────────────────────────────────────────────────

@app.post("/scan/frame")
async def scan_room_frame(req: ScanFrameRequest):
    """Process a base64 camera frame through LLM vision and return room state updates."""
    result = await asyncio.to_thread(scan_frame, req.image)
    return result


# ─── Phase 4B: Layout Intelligence ──────────────────────────────────────────

@app.get("/score")
async def get_layout_score():
    """5-dimension layout quality score for the current room state."""
    state = _build_scorer_state()
    return score_layout(state)


@app.get("/zones")
async def get_functional_zones():
    """Detect functional zones (living, sleep, work, dining) in the current room."""
    state = _build_scorer_state()
    return detect_zones(state)


@app.post("/goal")
async def set_design_goal(req: GoalRequest):
    """Accept a high-level design goal and return a multi-step action plan."""
    state = _build_scorer_state()
    plan  = await asyncio.to_thread(plan_goal, req.goal, state)
    # Record preference signal
    record_signal(req.session_id, "goal_set", req.goal)
    return plan


@app.post("/simulate")
async def simulate_actions(req: SimulateRequest):
    """What-if simulation: apply actions to a state copy and return score delta."""
    state  = _build_scorer_state()
    result = await asyncio.to_thread(simulate, state, req.actions)
    # Don't return full simulated_state in the response (too large)
    result.pop("simulated_state", None)
    return result


@app.post("/autofix")
async def autofix_layout():
    """
    Auto-fix the worst layout issues:
      1. Score current layout
      2. Find the lowest-scoring dimension
      3. Generate targeted fix plan
      4. Apply the plan
    """
    global _room_state
    state = _build_scorer_state()
    score = score_layout(state)

    # Find worst dimension
    dims   = score["dimensions"]
    worst  = min(dims, key=lambda k: dims[k]["score"])
    notes  = dims[worst]["notes"]
    issues = " | ".join(n for n in notes if n.startswith(("⚠", "⛔")))

    if not issues:
        return {"message": "Layout is already in good shape!", "score": score, "actions_applied": 0}

    goal = f"Fix these {worst.replace('_',' ')} issues: {issues[:200]}"
    plan = await asyncio.to_thread(plan_goal, goal, state)

    # Apply up to 5 actions from the plan
    actions_applied = 0
    for step in (plan.get("steps") or [])[:5]:
        action  = step.get("action", "")
        params  = step.get("params", {})
        command = f"{action} {json.dumps(params)}"
        try:
            new_state = await asyncio.to_thread(run_command, command, _room_state)
            _room_state = new_state
            actions_applied += 1
        except Exception:
            pass

    if actions_applied:
        await _broadcast(_room_state)

    new_score = score_layout(_build_scorer_state())
    return {
        "original_score":  score["overall"],
        "new_score":       new_score["overall"],
        "delta":           new_score["overall"] - score["overall"],
        "actions_applied": actions_applied,
        "plan":            plan,
        "state":           _state_to_dict(_room_state),
    }


@app.get("/preference/{session_id}")
async def get_preference_profile(session_id: str = "default"):
    """Return the preference profile for a session."""
    return get_preference_summary(session_id)


@app.post("/preference/{session_id}/signal")
async def post_preference_signal(session_id: str, req: PreferenceSignalRequest):
    """Record a preference signal for a session."""
    profile = record_signal(session_id, req.signal_type, req.value)
    return {"recorded": True, "session_id": session_id}


# ─── Phase 4D: AR Session Management ────────────────────────────────────────

@app.post("/ar/session")
async def create_ar_session():
    """Create a new AR session. Returns session token."""
    state   = _state_to_dict(_room_state)
    session = create_session(room_state=state)
    return {"token": session["token"], "expires_at": session["expires_at"]}


@app.get("/ar/session/{token}")
async def get_ar_session(token: str):
    """Get an AR session by token."""
    session = get_session(token)
    if not session:
        raise HTTPException(status_code=404, detail="AR session not found or expired")
    return session


@app.post("/ar/session/{token}/place")
async def ar_place(token: str, req: ARPlaceRequest):
    """Place a product in an AR session."""
    placement = ar_place_product(token, req.product_id, req.x, req.y, req.z, req.rotation, req.scale)
    if "error" in placement:
        raise HTTPException(status_code=404, detail=placement["error"])
    return placement


@app.post("/ar/session/{token}/capture")
async def ar_capture(token: str, req: ARCaptureRequest):
    """Save an AR screenshot or recording to a session."""
    result = ar_save_capture(token, req.type, req.data_url)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.get("/ar/session/{token}/qr")
async def ar_qr(token: str, base_url: str = Query(default="http://localhost:8000")):
    """Generate a QR code for cross-device AR session handoff."""
    session = get_session(token)
    if not session:
        raise HTTPException(status_code=404, detail="AR session not found")
    return generate_qr_code(token, base_url=base_url)


@app.post("/ar/session/{token}/save-to-design")
async def ar_save_to_design(token: str):
    """Convert AR session placements into RoomState ADD actions and apply them."""
    global _room_state
    actions = session_to_room_state_actions(token)
    if not actions:
        return {"message": "No AR placements to commit.", "actions_applied": 0}

    applied = 0
    for action in actions:
        try:
            params  = action["params"]
            command = f"ADD {json.dumps(params)}"
            new_state = await asyncio.to_thread(run_command, command, _room_state)
            _room_state = new_state
            applied += 1
        except Exception:
            pass

    await _broadcast(_room_state)
    return {
        "success":         True,
        "actions_applied": applied,
        "state":           _state_to_dict(_room_state),
    }


@app.get("/ar/product/{item_id}/preview")
async def ar_product_preview(item_id: str):
    """
    Return AR preview data for an IKEA Egypt product:
      - EGP price + all images (by type) + model_url for GLB AR viewer
      - Dimensions for 1:1 scale placement
    """
    from backend.scraper.catalog_writer import IKEACatalogDB
    db = IKEACatalogDB()
    product = db.get_by_id(item_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product not found: {item_id}")
    return {
        "item_no":           product.get("item_no"),
        "name":              product.get("name"),
        "series":            product.get("series"),
        "price":             product.get("price"),
        "currency":          product.get("currency", "EGP"),
        "image_url":         product.get("image_url"),
        "image_urls":        product.get("image_urls", []),
        "image_urls_by_type": product.get("image_urls_by_type", {}),
        "model_url":         product.get("model_url", ""),
        "width":             product.get("width"),
        "depth":             product.get("depth"),
        "height":            product.get("height"),
        "color_variants":    product.get("color_variants", []),
        "buy_url":           product.get("buy_url"),
        "ar_ready":          bool(product.get("model_url")),
    }


# ─── Phase 4D: Product Catalog (EGP) ────────────────────────────────────────

@app.get("/products/catalog")
async def get_products_catalog(
    category: str = Query(default="", description="Filter by furniture category"),
    q:        str = Query(default="", description="Search query"),
    limit:    int = Query(default=50,  ge=1, le=500),
    min_price: float = Query(default=0),
    max_price: float = Query(default=0),
    in_stock:  bool  = Query(default=False),
):
    """
    Query the IKEA Egypt SQLite catalog.
    Returns products with EGP prices, image galleries, and model URLs.
    """
    from backend.scraper.catalog_writer import IKEACatalogDB
    db = IKEACatalogDB()
    products = db.search(
        query=q,
        category=category,
        max_price=max_price,
        min_price=min_price,
        in_stock=in_stock,
        limit=limit,
    )
    stats = db.catalog_stats()
    return {
        "products": products,
        "total":    len(products),
        "catalog_stats": stats,
    }


# ─── Helper ───────────────────────────────────────────────────────────────────

def _build_scorer_state() -> dict:
    """Build a scorer-compatible state dict from current _room_state."""
    room    = _room_state.get("room", {})
    objects = _room_state.get("objects", [])
    windows = room.get("windows", [])
    doors   = room.get("doors",   [])

    # Normalise object format for scorer
    scorer_objects = []
    for obj in objects:
        w, d = (obj.get("size") or [1.0, 1.0]) + [1.0, 1.0]
        scorer_objects.append({
            "id":       obj.get("id", "?"),
            "type":     obj.get("type", "?"),
            "x":        float(obj.get("x", 0)),
            "z":        float(obj.get("z", 0)),
            "size":     [float(w), float(d)],
            "height":   float(obj.get("height", obj.get("h", 0.85))),
            "rotation": float(obj.get("rotation", 0)),
        })
    return {
        "objects":  scorer_objects,
        "width":    float(room.get("width",  10)),
        "depth":    float(room.get("height", 8)),
        "windows":  windows,
        "doors":    doors,
        "style":    _room_state.get("style", {}),
    }


# ─── Phase 4C: Floor Plan Editor ─────────────────────────────────────────────

from backend.floorplan.canvas_sync import (
    canvas_to_actions, room_state_to_canvas,
    list_templates, get_template,
)
from backend.floorplan.wall_builder import build_walls, infer_walls_from_room
from backend.floorplan.material_store import list_materials


class FloorplanSyncRequest(BaseModel):
    canvas_json:    dict  = {}
    room_width_cm:  float = 500.0
    room_depth_cm:  float = 400.0


class WallsRequest(BaseModel):
    walls: list                    # list of wall dicts from canvas


@app.post("/floorplan/sync")
async def floorplan_sync(req: FloorplanSyncRequest):
    """
    Receive Fabric.js canvas JSON, extract furniture positions as RoomState actions,
    apply them, and return an updated canvas JSON.
    """
    global _room_state
    actions = canvas_to_actions(req.canvas_json, req.room_width_cm, req.room_depth_cm)

    applied = 0
    for act in actions:
        try:
            command = f"{act['action']} {json.dumps(act['params'])}"
            new_state = await asyncio.to_thread(run_command, command, _room_state)
            _room_state = new_state
            applied += 1
        except Exception:
            pass

    if applied:
        await _broadcast(_room_state)

    return {
        "actions_applied": applied,
        "canvas_json":     room_state_to_canvas(_state_to_dict(_room_state)),
        "state":           _state_to_dict(_room_state),
    }


@app.post("/floorplan/walls")
async def build_wall_geometry(req: WallsRequest):
    """Convert 2D canvas walls into 3D geometry descriptors for Three.js rendering."""
    result = await asyncio.to_thread(build_walls, req.walls)
    return result


@app.get("/floorplan/walls/auto")
async def auto_generate_walls():
    """Auto-generate the 4 perimeter walls from the current room dimensions."""
    room = _room_state.get("room", {})
    w    = float(room.get("width",  5.0))
    d    = float(room.get("height", 4.0))
    windows = room.get("windows", [])
    doors   = room.get("doors",   [])
    walls   = infer_walls_from_room(w, d, doors=doors, windows=windows)
    return await asyncio.to_thread(build_walls, walls)


@app.get("/floorplan/export")
async def export_floorplan(format: str = Query(default="png", description="png | svg | pdf")):
    """
    Server-side floor plan export.
    For PDF: returns a plain PNG (full server-side PDF needs reportlab/weasyprint).
    """
    import io
    if format not in ("png", "svg", "pdf"):
        raise HTTPException(status_code=400, detail="format must be png, svg, or pdf")

    # Build canvas from current state
    canvas_json = room_state_to_canvas(_state_to_dict(_room_state))

    # For now return canvas JSON (frontend handles actual rendering)
    return {
        "format":      format,
        "canvas_json": canvas_json,
        "note":        "Use client-side export for rendered output",
    }


@app.get("/templates")
async def get_templates():
    """List all available room layout templates."""
    return {"templates": list_templates()}


@app.get("/templates/{template_id}")
async def get_single_template(template_id: str):
    """Return a full room layout template (with object list)."""
    t = get_template(template_id)
    if not t:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")
    return t


@app.get("/materials")
async def get_all_materials():
    """Return all available material swatches (floors, walls, furniture)."""
    return list_materials()


@app.get("/materials/{category}")
async def get_materials_by_category(category: str):
    """Return materials for a specific category: floors | walls | furniture."""
    all_mats = list_materials()
    if category not in all_mats:
        raise HTTPException(status_code=404, detail=f"Category '{category}' not found. Use: floors, walls, furniture")
    return {category: all_mats[category]}


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

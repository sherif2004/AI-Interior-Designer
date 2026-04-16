"""
FastAPI server — REST + WebSocket API for the AI Interior Designer.
"""
import os
import json
import asyncio
from contextlib import asynccontextmanager
from typing import Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path)

from backend.state.state_manager import RoomState, default_state
from backend.graph.designer_graph import run_command
from backend.environment.objects import FURNITURE_CATALOG
from backend.storage.project_store import list_projects

# ─────────────────────── App-level state ────────────────────────────────────

# In-memory session state (single room session)
_room_state: RoomState = default_state(
    room_width=float(os.getenv("ROOM_WIDTH", 10)),
    room_height=float(os.getenv("ROOM_HEIGHT", 8)),
)

# Active WebSocket connections
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
    yield  # startup / shutdown hooks (none needed currently)


app = FastAPI(
    title="AI Interior Designer API",
    version="1.0.0",
    description="Stateful AI room design system powered by LangGraph + OpenRouter",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend static files
_FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")


# ─────────────────────── Models ─────────────────────────────────────────────

class CommandRequest(BaseModel):
    command: str


class ResetRequest(BaseModel):
    width: float = 10.0
    height: float = 8.0


# ─────────────────────── Helper ─────────────────────────────────────────────

def _state_to_dict(state: RoomState) -> dict:
    return {
        "project": state.get("project", {}),
        "room": state.get("room", {}),
        "objects": state.get("objects", []),
        "history": state.get("history", []),
        "last_action": state.get("last_action", {}),
        "message": state.get("message", ""),
        "error": state.get("error"),
    }


# ─────────────────────── Routes ─────────────────────────────────────────────

@app.get("/")
async def root():
    """Serve frontend index.html if available, else API info."""
    index_path = os.path.join(_FRONTEND_DIR, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path)
    return {"message": "AI Interior Designer API", "docs": "/docs"}


@app.get("/health")
async def health():
    return {"status": "ok", "objects_in_room": len(_room_state.get("objects", []))}

import urllib.request
import urllib.error
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
    """Return the current room state."""
    return _state_to_dict(_room_state)


@app.get("/catalog")
async def get_catalog():
    """Return the furniture catalog."""
    return FURNITURE_CATALOG


@app.get("/projects")
async def get_projects():
    """Return saved projects."""
    return {"projects": list_projects()}


@app.post("/command")
async def post_command(req: CommandRequest):
    """
    Process a natural language command and update room state.
    Also broadcasts the new state to all WebSocket clients.
    """
    global _room_state

    if not req.command.strip():
        raise HTTPException(status_code=400, detail="Command cannot be empty")

    try:
        # Run the synchronous LangGraph brain in a separate thread globally
        # This prevents httpx sync client deadlocks inside the main async loop!
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
    """Reset the room to an empty state."""
    global _room_state
    _room_state = default_state(req.width, req.height)
    await _broadcast(_room_state)
    return {
        "success": True,
        "message": "Room has been reset.",
        "state": _state_to_dict(_room_state),
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time state streaming."""
    await websocket.accept()
    _ws_clients.add(websocket)
    try:
        # Send current state immediately on connect
        await websocket.send_text(json.dumps({
            "type": "state_update",
            "state": _state_to_dict(_room_state),
        }))
        # Keep connection alive
        while True:
            data = await websocket.receive_text()
            # Optionally handle commands over WebSocket too
            try:
                msg = json.loads(data)
                if msg.get("type") == "command":
                    await post_command(CommandRequest(command=msg.get("command", "")))
            except Exception:
                pass
    except WebSocketDisconnect:
        _ws_clients.discard(websocket)


# Mount static files at root (must be after all API routes)
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

"""
Simple JSON project persistence for AI Interior Designer.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from backend.state.state_manager import RoomState

PROJECTS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "projects"


def ensure_projects_dir() -> Path:
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    return PROJECTS_DIR


def project_path(project_id: str) -> Path:
    safe_id = project_id.strip().replace(" ", "_")
    return ensure_projects_dir() / f"{safe_id}.json"


def save_project(state: RoomState, project_id: Optional[str] = None) -> str:
    room = dict(state.get("room", {}))
    project = dict(state.get("project", {}))
    final_project_id = project_id or project.get("id") or "default_project"
    project.setdefault("id", final_project_id)
    project.setdefault("name", room.get("project_name", "My Home Project"))
    room["project_id"] = final_project_id

    state_to_save = {
        "project": project,
        "room": room,
        "objects": state.get("objects", []),
        "history": state.get("history", []),
        "last_action": state.get("last_action", {}),
        "message": state.get("message", ""),
        "error": state.get("error"),
    }

    path = project_path(final_project_id)
    path.write_text(json.dumps(state_to_save, indent=2), encoding="utf-8")
    return final_project_id


def load_project(project_id: str) -> RoomState:
    path = project_path(project_id)
    if not path.exists():
        raise FileNotFoundError(f"Project '{project_id}' not found")
    return json.loads(path.read_text(encoding="utf-8"))


def list_projects() -> list[dict]:
    ensure_projects_dir()
    projects = []
    for file in sorted(PROJECTS_DIR.glob("*.json")):
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
            projects.append({
                "id": data.get("project", {}).get("id", file.stem),
                "name": data.get("project", {}).get("name", file.stem),
                "room_type": data.get("room", {}).get("room_type", "generic"),
                "theme": data.get("room", {}).get("theme", "modern"),
            })
        except Exception:
            projects.append({"id": file.stem, "name": file.stem, "room_type": "unknown", "theme": "unknown"})
    return projects

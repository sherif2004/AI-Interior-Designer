"""
LangGraph Designer Graph — the AI brain of the interior designer.

Graph flow:
  START → llm_planner → action_dispatcher → END
           ↑________________________|  (on error, retry up to 2 times)
"""
import os
from typing import Literal
from dotenv import load_dotenv

from langgraph.graph import StateGraph, END, START
import json

from backend.state.state_manager import RoomState, default_state
from backend.llm.prompt import build_planner_prompt
from backend.llm.parser import parse_action
from backend.actions.add import handle_add
from backend.actions.move import handle_move
from backend.actions.rotate import handle_rotate
from backend.actions.delete import handle_delete
from backend.actions.style import (
    handle_set_wall_style,
    handle_set_floor_style,
    handle_set_room_style,
    handle_generate_layout,
)
from backend.actions.project import (
    handle_set_room_dimensions,
    handle_add_opening,
    handle_save_project,
    handle_load_project,
    handle_new_project,
)

# Evaluate path dynamically to backend/.env
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path)

MAX_RETRIES = 2


# ─────────────────────── LLM client (OpenRouter) ────────────────────────────

import urllib.request
import urllib.error

def call_openrouter(system_prompt: str, user_msg: str) -> str:
    url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    if not url.endswith("/chat/completions"):
        url = url.rstrip("/") + "/chat/completions"
        
    payload = {
        "model": os.getenv("OPENROUTER_MODEL", "anthropic/claude-3-haiku"),
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg}
        ],
        "temperature": 0.1,
        "max_tokens": 512
    }
    data = json.dumps(payload).encode("utf-8")
    
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {os.getenv('OPENROUTER_API_KEY', '')}")
    req.add_header("HTTP-Referer", "http://localhost:8000")
    req.add_header("X-Title", "AI-Interior-Designer")
    req.add_header("Content-Type", "application/json")
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            response_body = response.read().decode("utf-8")
            response_data = json.parse(response_body) if hasattr(json, 'parse') else json.loads(response_body)
            return response_data["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        try:
            err_dict = json.loads(err_msg)
            reason = err_dict.get("error", {}).get("message", err_msg)
        except Exception:
            reason = err_msg
        raise Exception(f"HTTP {e.code}: {reason}")
    except Exception as e:
        raise Exception(f"Network error: {str(e)}")


# ────────────────────────────── NODES ───────────────────────────────────────

def llm_planner_node(state: RoomState) -> RoomState:
    """
    Node 1: Call the LLM to parse the user command into a structured action.
    """
    command = state.get("user_command", "")
    if not command:
        return {**state, "error": "No command provided.", "pending_action": {}}

    system_prompt, user_msg = build_planner_prompt(command, state)

    try:
        raw_text = call_openrouter(system_prompt, user_msg)
    except Exception as e:
        return {**state, "error": f"LLM call failed: {str(e)}", "pending_action": {}}

    action = parse_action(raw_text)

    if action.get("type") == "ERROR":
        retry = state.get("retry_count", 0)
        return {
            **state,
            "error": action.get("reason", "LLM returned an error action"),
            "pending_action": action,
            "retry_count": retry + 1,
        }

    return {
        **state,
        "pending_action": action,
        "error": None,
        "retry_count": 0,
    }


def action_dispatcher_node(state: RoomState) -> RoomState:
    """
    Node 2: Execute the parsed action against the room state.
    """
    action = state.get("pending_action", {})
    action_type = action.get("type", "")

    if action_type == "ADD":
        return handle_add(state, action)

    elif action_type == "MOVE":
        return handle_move(state, action)

    elif action_type == "ROTATE":
        return handle_rotate(state, action)

    elif action_type == "DELETE":
        return handle_delete(state, action)

    elif action_type == "RESET":
        room = state.get("room", {})
        fresh = default_state(room.get("width", 10.0), room.get("height", 8.0))
        return {
            **fresh,
            "message": "🔄 Room has been reset. Starting fresh!",
            "history": state.get("history", []),
        }

    elif action_type == "SET_WALL_STYLE":
        return handle_set_wall_style(state, action)

    elif action_type == "SET_FLOOR_STYLE":
        return handle_set_floor_style(state, action)

    elif action_type == "SET_ROOM_STYLE":
        return handle_set_room_style(state, action)

    elif action_type == "GENERATE_LAYOUT":
        return handle_generate_layout(state, action)

    elif action_type == "SET_ROOM_DIMENSIONS":
        return handle_set_room_dimensions(state, action)

    elif action_type == "ADD_WINDOW":
        return handle_add_opening(state, action, "window")

    elif action_type == "ADD_DOOR":
        return handle_add_opening(state, action, "door")

    elif action_type == "SAVE_PROJECT":
        return handle_save_project(state, action)

    elif action_type == "LOAD_PROJECT":
        return handle_load_project(state, action)

    elif action_type == "NEW_PROJECT":
        return handle_new_project(state, action)

    elif action_type == "ERROR":
        reason = action.get("reason", "Unknown error")
        return {
            **state,
            "error": None,
            "message": f"❓ I couldn't understand that command: {reason}. Try something like 'Add a bed in the corner'.",
        }

    return {**state, "error": f"Unhandled action type: {action_type}"}


# ─────────────────────── CONDITIONAL EDGES ──────────────────────────────────

def should_retry(state: RoomState) -> Literal["retry", "dispatch", "end_with_error"]:
    """
    After llm_planner: retry on LLM error (up to MAX_RETRIES), else dispatch.
    """
    error = state.get("error")
    retry_count = state.get("retry_count", 0)

    if error and retry_count <= MAX_RETRIES:
        return "retry"
    if error and retry_count > MAX_RETRIES:
        return "end_with_error"
    return "dispatch"


def after_dispatch(state: RoomState) -> Literal["success", "error"]:
    if state.get("error"):
        return "error"
    return "success"


# ────────────────────── BUILD THE GRAPH ─────────────────────────────────────

def build_graph() -> StateGraph:
    graph = StateGraph(RoomState)

    graph.add_node("llm_planner", llm_planner_node)
    graph.add_node("action_dispatcher", action_dispatcher_node)

    graph.add_edge(START, "llm_planner")

    graph.add_conditional_edges(
        "llm_planner",
        should_retry,
        {
            "retry": "llm_planner",          # retry the LLM call
            "dispatch": "action_dispatcher",  # proceed to execution
            "end_with_error": END,            # give up
        },
    )

    graph.add_edge("action_dispatcher", END)

    return graph.compile()


# Singleton compiled graph (import this in the server)
designer_graph = build_graph()


def run_command(command: str, current_state: RoomState) -> RoomState:
    """
    Run one user command through the full LangGraph pipeline.
    Returns the updated RoomState.
    """
    # Append to history
    history = list(current_state.get("history", []))
    history.append(command)

    input_state = {
        **current_state,
        "user_command": command,
        "history": history,
        "retry_count": 0,
        "error": None,
    }

    result = designer_graph.invoke(input_state)

    # If graph ended with unresolved error, provide friendly message
    if result.get("error"):
        result["message"] = f"⚠️ {result['error']}"
        result["error"] = None

    return result

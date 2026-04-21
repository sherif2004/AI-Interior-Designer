"""
Preference Store — Phase 4B
============================
Learns from user behaviour across sessions to personalise future suggestions.
Persists per-session (or per-user) preference profiles to JSON files.

Tracked signals:
  - Furniture types added/deleted (reveal preferences)
  - Style themes applied
  - Budget ranges accepted
  - Layout goals set
"""

from __future__ import annotations
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger("preference_store")

DATA_DIR   = Path("data")
PREF_DIR   = DATA_DIR / "preferences"
PREF_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_PROFILE = {
    "session_id":     "default",
    "created_at":     "",
    "updated_at":     "",
    "style_votes":    {},   # {theme: count}
    "furniture_votes": {},  # {type: count}
    "budget_signals": [],   # [{"range": "low|mid|high", "ts": ...}]
    "goal_history":   [],   # ["Make it cozy", ...]
    "color_votes":    {},   # {"warm": count, "cool": count, "neutral": count}
}


def _profile_path(session_id: str) -> Path:
    safe = "".join(c for c in session_id if c.isalnum() or c in "_-")[:64]
    return PREF_DIR / f"{safe}.json"


def load_profile(session_id: str = "default") -> dict:
    path = _profile_path(session_id)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    profile = dict(DEFAULT_PROFILE)
    profile["session_id"] = session_id
    profile["created_at"] = datetime.now(timezone.utc).isoformat()
    return profile


def save_profile(profile: dict):
    profile["updated_at"] = datetime.now(timezone.utc).isoformat()
    path = _profile_path(profile.get("session_id", "default"))
    path.write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8")


def record_signal(session_id: str, signal_type: str, value: Any) -> dict:
    """
    Record a preference signal and return the updated profile.

    signal_type options:
      "furniture_added"   → value = furniture type string
      "furniture_deleted" → value = furniture type string (negative signal)
      "style_applied"     → value = theme string
      "goal_set"          → value = goal string
      "budget_range"      → value = "low" | "mid" | "high"
      "color_temp"        → value = "warm" | "cool" | "neutral"
    """
    profile = load_profile(session_id)
    ts = datetime.now(timezone.utc).isoformat()

    if signal_type == "furniture_added":
        profile["furniture_votes"][value] = profile["furniture_votes"].get(value, 0) + 1

    elif signal_type == "furniture_deleted":
        # Deletion is a weak negative signal — reduce or remove
        current = profile["furniture_votes"].get(value, 0)
        if current > 1:
            profile["furniture_votes"][value] = current - 1
        elif value in profile["furniture_votes"]:
            del profile["furniture_votes"][value]

    elif signal_type == "style_applied":
        profile["style_votes"][value] = profile["style_votes"].get(value, 0) + 1

    elif signal_type == "goal_set":
        profile["goal_history"].append({"goal": value, "ts": ts})
        profile["goal_history"] = profile["goal_history"][-20:]  # keep last 20

    elif signal_type == "budget_range":
        profile["budget_signals"].append({"range": value, "ts": ts})
        profile["budget_signals"] = profile["budget_signals"][-10:]

    elif signal_type == "color_temp":
        profile["color_votes"][value] = profile["color_votes"].get(value, 0) + 1

    save_profile(profile)
    return profile


def get_preference_summary(session_id: str = "default") -> dict:
    """
    Return a concise summary of inferred preferences for use in prompts.

    Returns:
        {
            "preferred_style":     "scandinavian",
            "preferred_furniture": ["sofa", "bookshelf"],
            "budget_tendency":     "mid",
            "color_temperature":   "warm",
            "recent_goals":        ["Make it cozy"],
            "confidence":          "low" | "medium" | "high"
        }
    """
    profile = load_profile(session_id)

    # Preferred style
    style_votes = profile.get("style_votes", {})
    preferred_style = max(style_votes, key=style_votes.get) if style_votes else None

    # Top 3 furniture preferences
    fv = profile.get("furniture_votes", {})
    preferred_furniture = sorted(fv, key=fv.get, reverse=True)[:3]

    # Budget tendency (mode of recent signals)
    budget_signals = profile.get("budget_signals", [])
    if budget_signals:
        from collections import Counter
        budget_tendency = Counter(b["range"] for b in budget_signals).most_common(1)[0][0]
    else:
        budget_tendency = None

    # Color temperature
    cv = profile.get("color_votes", {})
    color_temperature = max(cv, key=cv.get) if cv else None

    # Recent goals (last 3)
    goals = profile.get("goal_history", [])
    recent_goals = [g["goal"] for g in goals[-3:]]

    # Confidence based on signal count
    total_signals = sum(fv.values()) + sum(style_votes.values()) + len(budget_signals)
    confidence = "high" if total_signals >= 10 else "medium" if total_signals >= 4 else "low"

    return {
        "preferred_style":     preferred_style,
        "preferred_furniture": preferred_furniture,
        "budget_tendency":     budget_tendency,
        "color_temperature":   color_temperature,
        "recent_goals":        recent_goals,
        "confidence":          confidence,
        "total_signals":       total_signals,
    }

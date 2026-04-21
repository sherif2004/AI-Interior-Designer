"""
Phase 5.6 — HomeState (MVP)
Simple whole-home container for multiple RoomStates.
"""

from __future__ import annotations

from typing import TypedDict


class RoomConnection(TypedDict, total=False):
    a: str
    b: str
    type: str  # "door" | "hallway"


class HomeState(TypedDict, total=False):
    id: str
    name: str
    rooms: dict  # {room_id: RoomState-like dict}
    connections: list[RoomConnection]


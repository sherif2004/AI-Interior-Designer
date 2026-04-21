"""
Phase 5.5 — DXF export (MVP)
Generates a simple R12 DXF with:
  - room rectangle
  - furniture rectangles (top-down footprints)
Coordinates: meters in RoomState → DXF units (meters).
"""

from __future__ import annotations


def _line(x1, y1, x2, y2, layer="0") -> str:
    return "\n".join([
        "0", "LINE",
        "8", str(layer),
        "10", str(x1), "20", str(y1), "30", "0.0",
        "11", str(x2), "21", str(y2), "31", "0.0",
    ])


def export_room_dxf(state: dict) -> str:
    room = state.get("room", {}) or {}
    w = float(room.get("width", 10))
    d = float(room.get("height", 8))

    # Room outline in X/Y plane (Y represents Z from RoomState)
    ents = []
    ents.append(_line(0, 0, w, 0, layer="ROOM"))
    ents.append(_line(w, 0, w, d, layer="ROOM"))
    ents.append(_line(w, d, 0, d, layer="ROOM"))
    ents.append(_line(0, d, 0, 0, layer="ROOM"))

    for obj in state.get("objects", []) or []:
        x = float(obj.get("x", 0))
        z = float(obj.get("z", 0))
        ww = float(obj.get("w", (obj.get("size") or [1.0, 1.0])[0] if obj.get("size") else 1.0))
        dd = float(obj.get("d", (obj.get("size") or [1.0, 1.0])[1] if obj.get("size") else 1.0))
        layer = f"OBJ_{str(obj.get('type','furniture')).upper()}"
        ents.append(_line(x, z, x + ww, z, layer=layer))
        ents.append(_line(x + ww, z, x + ww, z + dd, layer=layer))
        ents.append(_line(x + ww, z + dd, x, z + dd, layer=layer))
        ents.append(_line(x, z + dd, x, z, layer=layer))

    body = "\n".join(ents)
    return "\n".join([
        "0", "SECTION",
        "2", "HEADER",
        "0", "ENDSEC",
        "0", "SECTION",
        "2", "ENTITIES",
        body,
        "0", "ENDSEC",
        "0", "EOF",
        "",
    ])


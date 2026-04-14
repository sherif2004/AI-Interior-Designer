"""
Room environment definition.
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Room:
    width: float = 10.0   # meters (X axis)
    height: float = 8.0   # meters (Z axis)
    wall_thickness: float = 0.2

    # Structural elements (fixed constraints)
    doors: list[dict] = field(default_factory=lambda: [
        {"wall": "south", "position": 0.5, "width": 0.9}
    ])
    windows: list[dict] = field(default_factory=lambda: [
        {"wall": "north", "position": 0.3, "width": 1.2},
        {"wall": "east",  "position": 0.6, "width": 1.0},
    ])

    def to_dict(self) -> dict:
        return {
            "width": self.width,
            "height": self.height,
            "wall_thickness": self.wall_thickness,
            "doors": self.doors,
            "windows": self.windows,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Room":
        return cls(
            width=data.get("width", 10.0),
            height=data.get("height", 8.0),
            wall_thickness=data.get("wall_thickness", 0.2),
            doors=data.get("doors", []),
            windows=data.get("windows", []),
        )

    def is_within_bounds(self, x: float, z: float, w: float, d: float) -> bool:
        """Return True if an object fits inside the room boundaries."""
        margin = self.wall_thickness
        return (
            x >= margin
            and z >= margin
            and (x + w) <= (self.width - margin)
            and (z + d) <= (self.height - margin)
        )

    def clamp_to_room(self, x: float, z: float, w: float, d: float) -> tuple[float, float]:
        """Clamp position so the object stays inside room bounds."""
        margin = self.wall_thickness
        x = max(margin, min(x, self.width - margin - w))
        z = max(margin, min(z, self.height - margin - d))
        return x, z

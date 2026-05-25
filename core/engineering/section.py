from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class SectionDefinition:
    id: str
    name: str
    material_id: str
    thickness: float
    plane_mode: str = "stress"

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("SectionDefinition.id must not be empty")
        if not self.name:
            raise ValueError("SectionDefinition.name must not be empty")
        if not self.material_id:
            raise ValueError("SectionDefinition.material_id must not be empty")
        if self.thickness <= 0.0:
            raise ValueError("SectionDefinition.thickness must be positive")
        if self.plane_mode not in {"stress", "strain"}:
            raise ValueError("SectionDefinition.plane_mode must be 'stress' or 'strain'")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "material_id": self.material_id,
            "thickness": self.thickness,
            "plane_mode": self.plane_mode,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SectionDefinition":
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            material_id=str(data["material_id"]),
            thickness=float(data["thickness"]),
            plane_mode=str(data.get("plane_mode", "stress")),
        )

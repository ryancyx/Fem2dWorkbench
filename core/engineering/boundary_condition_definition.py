from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class BoundaryConditionDefinition:
    id: str
    name: str
    step_id: str
    target_type: str
    target_id: str
    ux_fixed: bool = False
    uy_fixed: bool = False
    ux_value: float = 0.0
    uy_value: float = 0.0

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("BoundaryConditionDefinition.id must not be empty")
        if not self.name:
            raise ValueError("BoundaryConditionDefinition.name must not be empty")
        if not self.step_id:
            raise ValueError("BoundaryConditionDefinition.step_id must not be empty")
        if self.target_type != "geometry_edge":
            raise ValueError("BoundaryConditionDefinition.target_type must be 'geometry_edge'")
        if not self.target_id:
            raise ValueError("BoundaryConditionDefinition.target_id must not be empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "step_id": self.step_id,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "ux_fixed": self.ux_fixed,
            "uy_fixed": self.uy_fixed,
            "ux_value": self.ux_value,
            "uy_value": self.uy_value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BoundaryConditionDefinition":
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            step_id=str(data["step_id"]),
            target_type=str(data["target_type"]),
            target_id=str(data["target_id"]),
            ux_fixed=bool(data.get("ux_fixed", False)),
            uy_fixed=bool(data.get("uy_fixed", False)),
            ux_value=float(data.get("ux_value", 0.0)),
            uy_value=float(data.get("uy_value", 0.0)),
        )

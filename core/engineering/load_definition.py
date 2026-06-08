from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class LoadDefinition:
    id: str
    name: str
    step_id: str
    target_type: str
    target_id: str
    load_type: str
    qx: float = 0.0
    qy: float = 0.0
    start_t: float = 0.0
    end_t: float = 1.0

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("LoadDefinition.id must not be empty")
        if not self.name:
            raise ValueError("LoadDefinition.name must not be empty")
        if not self.step_id:
            raise ValueError("LoadDefinition.step_id must not be empty")
        if self.target_type == "geometry_edge_segment":
            self.target_type = "geometry_edge"
        if self.target_type not in {"geometry_edge", "geometry_point"}:
            raise ValueError(
                "LoadDefinition.target_type must be 'geometry_edge' or 'geometry_point'"
            )
        if not self.target_id:
            raise ValueError("LoadDefinition.target_id must not be empty")
        if self.load_type not in {"edge_uniform", "nodal_concentrated"}:
            raise ValueError(
                "LoadDefinition.load_type must be 'edge_uniform' or 'nodal_concentrated'"
            )
        if self.load_type == "nodal_concentrated":
            if self.target_type != "geometry_point":
                raise ValueError("Nodal concentrated loads must target geometry_point")
            self.start_t = 0.0
            self.end_t = 1.0
        else:
            if self.target_type != "geometry_edge":
                raise ValueError("Edge uniform loads must target geometry_edge")
            start_t = float(self.start_t)
            end_t = float(self.end_t)
            self.start_t = min(start_t, end_t)
            self.end_t = max(start_t, end_t)
            if self.start_t < 0.0 or self.end_t > 1.0:
                raise ValueError("LoadDefinition edge segment range must stay within [0, 1]")
            if self.end_t - self.start_t <= 1.0e-9:
                raise ValueError("LoadDefinition edge segment range is too short")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "step_id": self.step_id,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "load_type": self.load_type,
            "qx": self.qx,
            "qy": self.qy,
            "start_t": self.start_t,
            "end_t": self.end_t,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LoadDefinition":
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            step_id=str(data["step_id"]),
            target_type=str(data["target_type"]),
            target_id=str(data["target_id"]),
            load_type=str(data["load_type"]),
            qx=float(data.get("qx", 0.0)),
            qy=float(data.get("qy", 0.0)),
            start_t=float(data.get("start_t", 0.0)),
            end_t=float(data.get("end_t", 1.0)),
        )

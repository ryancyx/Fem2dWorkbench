from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class PartInstance:
    id: str
    name: str
    part_id: str
    translation_x: float = 0.0
    translation_y: float = 0.0
    rotation_degrees: float = 0.0

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("PartInstance.id must not be empty")
        if not self.name:
            raise ValueError("PartInstance.name must not be empty")
        if not self.part_id:
            raise ValueError("PartInstance.part_id must not be empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "part_id": self.part_id,
            "translation_x": self.translation_x,
            "translation_y": self.translation_y,
            "rotation_degrees": self.rotation_degrees,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PartInstance":
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            part_id=str(data["part_id"]),
            translation_x=float(data.get("translation_x", 0.0)),
            translation_y=float(data.get("translation_y", 0.0)),
            rotation_degrees=float(data.get("rotation_degrees", 0.0)),
        )


@dataclass(slots=True)
class Assembly:
    instances: list[PartInstance] = field(default_factory=list)

    def __post_init__(self) -> None:
        ids = [instance.id for instance in self.instances]
        if len(ids) != len(set(ids)):
            raise ValueError("Assembly.instances contains duplicate ids")

    def to_dict(self) -> dict[str, Any]:
        return {"instances": [instance.to_dict() for instance in self.instances]}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Assembly":
        return cls(instances=[PartInstance.from_dict(item) for item in data.get("instances", [])])

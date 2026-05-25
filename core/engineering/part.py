from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.engineering.geometry import GeometryModel


@dataclass(slots=True)
class Part:
    id: str
    name: str
    geometry: GeometryModel
    section_id: str | None = None

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Part.id must not be empty")
        if not self.name:
            raise ValueError("Part.name must not be empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "geometry": self.geometry.to_dict(),
            "section_id": self.section_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Part":
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            geometry=GeometryModel.from_dict(data["geometry"]),
            section_id=data.get("section_id"),
        )

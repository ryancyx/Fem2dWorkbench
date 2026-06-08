from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class MaterialDefinition:
    id: str
    name: str
    young_modulus: float
    poisson_ratio: float
    color: str = "#808080"
    unit_weight: float = 0.0

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("MaterialDefinition.id must not be empty")
        if not self.name:
            raise ValueError("MaterialDefinition.name must not be empty")
        if self.young_modulus <= 0.0:
            raise ValueError("MaterialDefinition.young_modulus must be positive")
        if not (-1.0 < self.poisson_ratio < 0.5):
            raise ValueError("MaterialDefinition.poisson_ratio must be between -1.0 and 0.5")
        if self.unit_weight < 0.0:
            raise ValueError("MaterialDefinition.unit_weight must be non-negative")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "young_modulus": self.young_modulus,
            "poisson_ratio": self.poisson_ratio,
            "color": self.color,
            "unit_weight": self.unit_weight,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MaterialDefinition":
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            young_modulus=float(data["young_modulus"]),
            poisson_ratio=float(data["poisson_ratio"]),
            color=str(data.get("color", "#808080")),
            unit_weight=float(data.get("unit_weight", 0.0) or 0.0),
        )

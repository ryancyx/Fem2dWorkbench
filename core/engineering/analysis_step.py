from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class AnalysisStep:
    id: str
    name: str
    step_type: str = "static_linear"

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("AnalysisStep.id must not be empty")
        if not self.name:
            raise ValueError("AnalysisStep.name must not be empty")
        if self.step_type != "static_linear":
            raise ValueError("AnalysisStep.step_type must be 'static_linear'")

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name, "step_type": self.step_type}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AnalysisStep":
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            step_type=str(data.get("step_type", "static_linear")),
        )

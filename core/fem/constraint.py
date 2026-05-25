from dataclasses import dataclass, asdict


@dataclass
class Constraint:
    id: int
    node_id: int
    ux_fixed: bool = False
    uy_fixed: bool = False
    ux_value: float = 0.0
    uy_value: float = 0.0

    def __post_init__(self) -> None:
        if not self.ux_fixed and self.ux_value != 0.0:
            raise ValueError("when ux_fixed = False, ux_value must be 0.0")
        if not self.uy_fixed and self.uy_value != 0.0:
            raise ValueError("when uy_fixed = False, uy_value must be 0.0")
        if not self.ux_fixed and not self.uy_fixed:
            raise ValueError("Constraint must fix at least one direction(ux or uy)")

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Constraint":
        return cls(**data)

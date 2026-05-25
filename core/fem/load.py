from dataclasses import dataclass, asdict


@dataclass
class Load:
    id: int
    node_id: int
    fx: float = 0.0
    fy: float = 0.0
    load_type: str = "nodal"

    def __post_init__(self) -> None:
        if self.load_type != "nodal":
            raise ValueError("Load type must be nodal")
        if self.fx == 0.0 and self.fy == 0.0:
            raise ValueError("Fx & Fy must not both be zero")

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Load":
        return cls(**data)

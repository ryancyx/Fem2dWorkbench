from dataclasses import dataclass, asdict


@dataclass
class Node:
    id: int
    x: float
    y: float

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'Node':
        return cls(**data)


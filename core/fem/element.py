from dataclasses import dataclass, asdict


@dataclass
class Element:
    id: int
    node_ids: list[int]
    material_id: int | None = None
    element_type: str = "CST"

    def __post_init__(self) -> None:
        if self.element_type != "CST":
            raise ValueError(f"当前仅支持 CST 三节点三角形单元，收到:{self.element_type}")
        if len(self.node_ids) != 3:
            raise ValueError(f"CST 单元节点数为3, 当前收到 {len(self.node_ids)} 个")
        if len(set(self.node_ids)) != 3:
            raise ValueError(f"CST 单元节点不可重复")

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Element":
        return cls(**data)

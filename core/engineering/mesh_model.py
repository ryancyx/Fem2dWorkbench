from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class MeshNode:
    id: int
    x: float
    y: float

    def __post_init__(self) -> None:
        if self.id <= 0:
            raise ValueError("MeshNode.id must be positive")

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "x": self.x, "y": self.y}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MeshNode":
        return cls(id=int(data["id"]), x=float(data["x"]), y=float(data["y"]))


@dataclass(slots=True)
class MeshElement:
    id: int
    node_ids: list[int]
    element_type: str = "CST"
    source_face_id: str | None = None

    def __post_init__(self) -> None:
        if self.id <= 0:
            raise ValueError("MeshElement.id must be positive")
        if self.element_type != "CST":
            raise ValueError("MeshElement.element_type must be 'CST'")
        if len(self.node_ids) != 3:
            raise ValueError("MeshElement.node_ids must contain exactly 3 node ids")
        if len(set(self.node_ids)) != 3:
            raise ValueError("MeshElement.node_ids must not contain duplicates")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "node_ids": list(self.node_ids),
            "element_type": self.element_type,
            "source_face_id": self.source_face_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MeshElement":
        return cls(
            id=int(data["id"]),
            node_ids=[int(node_id) for node_id in data["node_ids"]],
            element_type=str(data.get("element_type", "CST")),
            source_face_id=data.get("source_face_id"),
        )


@dataclass(slots=True)
class MeshModel:
    nodes: list[MeshNode] = field(default_factory=list)
    elements: list[MeshElement] = field(default_factory=list)
    geometry_edge_to_mesh_node_ids: dict[str, list[int]] = field(default_factory=dict)
    geometry_edge_to_mesh_element_edges: dict[str, list[tuple[int, int, int]]] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        self.validate()

    def get_node_by_id(self, node_id: int) -> MeshNode | None:
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None

    def get_element_by_id(self, element_id: int) -> MeshElement | None:
        for element in self.elements:
            if element.id == element_id:
                return element
        return None

    def validate(self) -> None:
        node_ids = [node.id for node in self.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("MeshModel.nodes contains duplicate ids")

        element_ids = [element.id for element in self.elements]
        if len(element_ids) != len(set(element_ids)):
            raise ValueError("MeshModel.elements contains duplicate ids")

        node_id_set = set(node_ids)
        element_id_set = set(element_ids)

        for element in self.elements:
            for node_id in element.node_ids:
                if node_id not in node_id_set:
                    raise ValueError(
                        f"MeshElement {element.id!r} references unknown node {node_id!r}"
                    )

        for edge_id, mapped_node_ids in self.geometry_edge_to_mesh_node_ids.items():
            if not edge_id:
                raise ValueError("Geometry edge ids must not be empty")
            for node_id in mapped_node_ids:
                if node_id not in node_id_set:
                    raise ValueError(
                        f"Geometry edge {edge_id!r} references unknown mesh node {node_id!r}"
                    )

        for edge_id, element_edges in self.geometry_edge_to_mesh_element_edges.items():
            if not edge_id:
                raise ValueError("Geometry edge ids must not be empty")
            for element_id, local_a, local_b in element_edges:
                if element_id not in element_id_set:
                    raise ValueError(
                        f"Geometry edge {edge_id!r} references unknown element {element_id!r}"
                    )
                if local_a not in {0, 1, 2} or local_b not in {0, 1, 2}:
                    raise ValueError("Mesh element local node indices must be 0, 1, or 2")
                if local_a == local_b:
                    raise ValueError("Mesh element edge local node indices must be different")

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [node.to_dict() for node in self.nodes],
            "elements": [element.to_dict() for element in self.elements],
            "geometry_edge_to_mesh_node_ids": {
                edge_id: list(node_ids)
                for edge_id, node_ids in self.geometry_edge_to_mesh_node_ids.items()
            },
            "geometry_edge_to_mesh_element_edges": {
                edge_id: [list(item) for item in element_edges]
                for edge_id, element_edges in self.geometry_edge_to_mesh_element_edges.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MeshModel":
        return cls(
            nodes=[MeshNode.from_dict(item) for item in data.get("nodes", [])],
            elements=[MeshElement.from_dict(item) for item in data.get("elements", [])],
            geometry_edge_to_mesh_node_ids={
                str(edge_id): [int(node_id) for node_id in node_ids]
                for edge_id, node_ids in data.get("geometry_edge_to_mesh_node_ids", {}).items()
            },
            geometry_edge_to_mesh_element_edges={
                str(edge_id): [
                    (int(element_id), int(local_a), int(local_b))
                    for element_id, local_a, local_b in element_edges
                ]
                for edge_id, element_edges in data.get(
                    "geometry_edge_to_mesh_element_edges", {}
                ).items()
            },
        )

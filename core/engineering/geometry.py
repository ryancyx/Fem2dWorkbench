from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class GeometryPoint:
    id: str
    x: float
    y: float

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("GeometryPoint.id must not be empty")

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "x": self.x, "y": self.y}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GeometryPoint":
        return cls(id=str(data["id"]), x=float(data["x"]), y=float(data["y"]))


@dataclass(slots=True)
class GeometryEdge:
    id: str
    start_point_id: str
    end_point_id: str

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("GeometryEdge.id must not be empty")
        if not self.start_point_id or not self.end_point_id:
            raise ValueError("GeometryEdge point references must not be empty")
        if self.start_point_id == self.end_point_id:
            raise ValueError("GeometryEdge endpoints must be different")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "start_point_id": self.start_point_id,
            "end_point_id": self.end_point_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GeometryEdge":
        return cls(
            id=str(data["id"]),
            start_point_id=str(data["start_point_id"]),
            end_point_id=str(data["end_point_id"]),
        )


@dataclass(slots=True)
class GeometryFace:
    id: str
    edge_ids: list[str]
    point_ids: list[str] = field(default_factory=list)
    section_id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("GeometryFace.id must not be empty")
        if not self.edge_ids:
            raise ValueError("GeometryFace.edge_ids must not be empty")
        if self.point_ids and len(self.point_ids) < 3:
            raise ValueError("GeometryFace.point_ids must contain at least 3 points when provided")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "edge_ids": list(self.edge_ids),
            "point_ids": list(self.point_ids),
            "section_id": self.section_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GeometryFace":
        return cls(
            id=str(data["id"]),
            edge_ids=[str(edge_id) for edge_id in data["edge_ids"]],
            point_ids=[str(point_id) for point_id in data.get("point_ids", [])],
            section_id=str(data.get("section_id", "") or ""),
        )


@dataclass(slots=True)
class GeometryModel:
    points: list[GeometryPoint] = field(default_factory=list)
    edges: list[GeometryEdge] = field(default_factory=list)
    faces: list[GeometryFace] = field(default_factory=list)
    _normalization_stats: dict[str, Any] = field(default_factory=dict, repr=False)
    _face_build_stats: dict[str, Any] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        self._validate_unique_ids("points", [point.id for point in self.points])
        self._validate_unique_ids("edges", [edge.id for edge in self.edges])
        self._validate_unique_ids("faces", [face.id for face in self.faces])

        point_ids = {point.id for point in self.points}
        edge_ids = {edge.id for edge in self.edges}
        for edge in self.edges:
            if edge.start_point_id not in point_ids or edge.end_point_id not in point_ids:
                raise ValueError(f"GeometryEdge {edge.id!r} references unknown points")
        for face in self.faces:
            missing_edges = [edge_id for edge_id in face.edge_ids if edge_id not in edge_ids]
            if missing_edges:
                raise ValueError(f"GeometryFace {face.id!r} references unknown edges: {missing_edges}")
            missing_points = [point_id for point_id in face.point_ids if point_id not in point_ids]
            if missing_points:
                raise ValueError(f"GeometryFace {face.id!r} references unknown points: {missing_points}")

    @staticmethod
    def _validate_unique_ids(label: str, ids: list[str]) -> None:
        if len(ids) != len(set(ids)):
            raise ValueError(f"GeometryModel.{label} contains duplicate ids")

    @classmethod
    def create_rectangle(
        cls,
        width: float,
        height: float,
        origin_x: float = 0.0,
        origin_y: float = 0.0,
    ) -> "GeometryModel":
        if width <= 0.0:
            raise ValueError("Rectangle width must be positive")
        if height <= 0.0:
            raise ValueError("Rectangle height must be positive")

        points = [
            GeometryPoint(id="p1", x=origin_x, y=origin_y),
            GeometryPoint(id="p2", x=origin_x + width, y=origin_y),
            GeometryPoint(id="p3", x=origin_x + width, y=origin_y + height),
            GeometryPoint(id="p4", x=origin_x, y=origin_y + height),
        ]
        edges = [
            GeometryEdge(id="bottom", start_point_id="p1", end_point_id="p2"),
            GeometryEdge(id="right", start_point_id="p2", end_point_id="p3"),
            GeometryEdge(id="top", start_point_id="p3", end_point_id="p4"),
            GeometryEdge(id="left", start_point_id="p4", end_point_id="p1"),
        ]
        faces = [GeometryFace(id="face", edge_ids=["bottom", "right", "top", "left"], point_ids=["p1", "p2", "p3", "p4"])]
        return cls(points=points, edges=edges, faces=faces)

    def to_dict(self) -> dict[str, Any]:
        return {
            "points": [point.to_dict() for point in self.points],
            "edges": [edge.to_dict() for edge in self.edges],
            "faces": [face.to_dict() for face in self.faces],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GeometryModel":
        return cls(
            points=[GeometryPoint.from_dict(item) for item in data.get("points", [])],
            edges=[GeometryEdge.from_dict(item) for item in data.get("edges", [])],
            faces=[GeometryFace.from_dict(item) for item in data.get("faces", [])],
        )

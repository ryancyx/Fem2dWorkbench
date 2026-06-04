from __future__ import annotations

from collections import defaultdict, deque
from typing import Iterable

from core.engineering.geometry import (
    GeometryEdge,
    GeometryFace,
    GeometryModel,
    GeometryPoint,
)


def create_empty_sketch_geometry() -> GeometryModel:
    return GeometryModel(points=[], edges=[], faces=[])


def is_sketch_geometry(geometry: GeometryModel) -> bool:
    return hasattr(geometry, "points") and hasattr(geometry, "edges") and hasattr(geometry, "faces")


def get_sketch_points(geometry: GeometryModel) -> list[dict]:
    return [{"id": point.id, "x": point.x, "y": point.y} for point in geometry.points]


def get_sketch_edges(geometry: GeometryModel) -> list[dict]:
    return [
        {
            "id": edge.id,
            "start_point_id": edge.start_point_id,
            "end_point_id": edge.end_point_id,
        }
        for edge in geometry.edges
    ]


def get_sketch_faces(geometry: GeometryModel) -> list[dict]:
    return [{"id": face.id, "edge_ids": list(face.edge_ids)} for face in geometry.faces]


def create_unique_point_id(geometry: GeometryModel, base_id: str = "p") -> str:
    return _create_unique_numbered_id((point.id for point in geometry.points), base_id)


def create_unique_edge_id(geometry: GeometryModel, base_id: str = "e") -> str:
    return _create_unique_numbered_id((edge.id for edge in geometry.edges), base_id)


def create_unique_face_id(geometry: GeometryModel, base_id: str = "f") -> str:
    return _create_unique_numbered_id((face.id for face in geometry.faces), base_id)


def add_sketch_point(geometry: GeometryModel, x: float, y: float) -> GeometryModel:
    geometry.points.append(
        GeometryPoint(
            id=create_unique_point_id(geometry),
            x=float(x),
            y=float(y),
        )
    )
    return geometry


def move_sketch_point(
    geometry: GeometryModel,
    point_id: str,
    x: float,
    y: float,
) -> GeometryModel:
    point = _require_point(geometry, point_id)
    point.x = float(x)
    point.y = float(y)
    return geometry


def delete_sketch_point(geometry: GeometryModel, point_id: str) -> GeometryModel:
    _require_point(geometry, point_id)
    geometry.points = [point for point in geometry.points if point.id != point_id]
    geometry.edges = [
        edge
        for edge in geometry.edges
        if edge.start_point_id != point_id and edge.end_point_id != point_id
    ]
    geometry.faces = []
    return geometry


def add_sketch_edge(
    geometry: GeometryModel,
    start_point_id: str,
    end_point_id: str,
) -> GeometryModel:
    _require_point(geometry, start_point_id)
    _require_point(geometry, end_point_id)
    if start_point_id == end_point_id:
        raise ValueError("Sketch edge endpoints must be different")
    if _edge_exists_between(geometry, start_point_id, end_point_id):
        raise ValueError(f"Sketch edge already exists between {start_point_id!r} and {end_point_id!r}")

    geometry.edges.append(
        GeometryEdge(
            id=create_unique_edge_id(geometry),
            start_point_id=start_point_id,
            end_point_id=end_point_id,
        )
    )
    geometry.faces = []
    return geometry


def delete_sketch_edge(geometry: GeometryModel, edge_id: str) -> GeometryModel:
    _require_edge(geometry, edge_id)
    geometry.edges = [edge for edge in geometry.edges if edge.id != edge_id]
    geometry.faces = []
    return geometry


def can_build_single_closed_face(geometry: GeometryModel) -> bool:
    if len(geometry.edges) < 3:
        return False

    point_ids = {point.id for point in geometry.points}
    adjacency: dict[str, set[str]] = defaultdict(set)
    degree: dict[str, int] = defaultdict(int)
    participating_points: set[str] = set()

    for edge in geometry.edges:
        if edge.start_point_id not in point_ids or edge.end_point_id not in point_ids:
            return False
        adjacency[edge.start_point_id].add(edge.end_point_id)
        adjacency[edge.end_point_id].add(edge.start_point_id)
        degree[edge.start_point_id] += 1
        degree[edge.end_point_id] += 1
        participating_points.add(edge.start_point_id)
        participating_points.add(edge.end_point_id)

    if len(participating_points) < 3:
        return False
    if any(degree[point_id] != 2 for point_id in participating_points):
        return False

    visited = _connected_component(next(iter(participating_points)), adjacency)
    return visited == participating_points


def build_single_face_from_edges(geometry: GeometryModel) -> GeometryModel:
    if not can_build_single_closed_face(geometry):
        raise ValueError("Sketch edges do not form a single closed face")

    geometry.faces = [
        GeometryFace(
            id=create_unique_face_id(geometry),
            edge_ids=[edge.id for edge in geometry.edges],
        )
    ]
    return geometry


def clear_sketch_geometry(geometry: GeometryModel) -> GeometryModel:
    geometry.points = []
    geometry.edges = []
    geometry.faces = []
    return geometry


def create_geometry_from_polygon_points(points: list[tuple[float, float]]) -> GeometryModel:
    if len(points) < 3:
        raise ValueError("Polygon sketch requires at least 3 points")

    geometry = create_empty_sketch_geometry()
    for x, y in points:
        add_sketch_point(geometry, x, y)

    point_ids = [point.id for point in geometry.points]
    for index, start_point_id in enumerate(point_ids):
        end_point_id = point_ids[(index + 1) % len(point_ids)]
        add_sketch_edge(geometry, start_point_id, end_point_id)

    build_single_face_from_edges(geometry)
    return geometry


def _create_unique_numbered_id(existing_ids: Iterable[str], base_id: str) -> str:
    existing = set(existing_ids)
    index = 1
    while True:
        candidate = f"{base_id}{index}"
        if candidate not in existing:
            return candidate
        index += 1


def _require_point(geometry: GeometryModel, point_id: str) -> GeometryPoint:
    for point in geometry.points:
        if point.id == point_id:
            return point
    raise ValueError(f"Unknown sketch point id: {point_id}")


def _require_edge(geometry: GeometryModel, edge_id: str) -> GeometryEdge:
    for edge in geometry.edges:
        if edge.id == edge_id:
            return edge
    raise ValueError(f"Unknown sketch edge id: {edge_id}")


def _edge_exists_between(
    geometry: GeometryModel,
    start_point_id: str,
    end_point_id: str,
) -> bool:
    endpoints = {start_point_id, end_point_id}
    return any({edge.start_point_id, edge.end_point_id} == endpoints for edge in geometry.edges)


def _connected_component(start_point_id: str, adjacency: dict[str, set[str]]) -> set[str]:
    visited: set[str] = set()
    queue: deque[str] = deque([start_point_id])
    while queue:
        point_id = queue.popleft()
        if point_id in visited:
            continue
        visited.add(point_id)
        queue.extend(adjacency[point_id] - visited)
    return visited

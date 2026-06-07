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
    return [
        {
            "id": face.id,
            "edge_ids": list(face.edge_ids),
            "section_id": face.section_id,
        }
        for face in geometry.faces
    ]


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
    try:
        return len(_collect_closed_loops(geometry)) == 1
    except ValueError:
        return False


def build_single_face_from_edges(geometry: GeometryModel) -> GeometryModel:
    loop_rows = _collect_closed_loops(geometry)
    if len(loop_rows) != 1:
        raise ValueError("Sketch edges do not form a single closed face")
    geometry.faces = [GeometryFace(id="f1", edge_ids=list(loop_rows[0]["edge_ids"]))]
    return geometry


def build_faces_from_edges(geometry: GeometryModel) -> GeometryModel:
    loop_rows = _collect_closed_loops(geometry)
    geometry.faces = [
        GeometryFace(id=f"f{index}", edge_ids=list(loop_row["edge_ids"]))
        for index, loop_row in enumerate(loop_rows, start=1)
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


def _collect_closed_loops(geometry: GeometryModel) -> list[dict[str, object]]:
    if len(geometry.edges) < 3:
        raise ValueError("Sketch edges must contain at least 3 edges")

    point_by_id = {point.id: point for point in geometry.points}
    edge_by_id = {edge.id: edge for edge in geometry.edges}
    adjacency: dict[str, list[tuple[str, str]]] = defaultdict(list)
    edge_id_by_endpoint_pair: dict[frozenset[str], str] = {}
    participating_points: set[str] = set()

    for edge in geometry.edges:
        if edge.start_point_id not in point_by_id or edge.end_point_id not in point_by_id:
            raise ValueError(f"Sketch edge {edge.id!r} references unknown points")
        endpoint_pair = frozenset((edge.start_point_id, edge.end_point_id))
        if endpoint_pair in edge_id_by_endpoint_pair:
            raise ValueError("Sketch contains duplicate edges between the same points")
        edge_id_by_endpoint_pair[endpoint_pair] = edge.id
        adjacency[edge.start_point_id].append((edge.end_point_id, edge.id))
        adjacency[edge.end_point_id].append((edge.start_point_id, edge.id))
        participating_points.add(edge.start_point_id)
        participating_points.add(edge.end_point_id)

    if len(participating_points) < 3:
        raise ValueError("Sketch edges must contain at least 3 participating points")
    for point_id in participating_points:
        if len(adjacency[point_id]) != 2:
            raise ValueError("Only simple disjoint closed loops are supported")

    components = _connected_components(participating_points, adjacency)
    loop_rows: list[dict[str, object]] = []
    for component in components:
        component_edges = [
            edge
            for edge in geometry.edges
            if edge.start_point_id in component and edge.end_point_id in component
        ]
        ordered_point_ids = _ordered_component_point_ids(
            component=component,
            point_by_id=point_by_id,
            adjacency=adjacency,
            edge_id_by_endpoint_pair=edge_id_by_endpoint_pair,
            expected_edge_count=len(component_edges),
        )
        ordered_points = [(point_by_id[point_id].x, point_by_id[point_id].y) for point_id in ordered_point_ids]
        if _has_self_intersections(ordered_points):
            raise ValueError("Self-intersecting closed loops are not supported")
        if _signed_area_xy(ordered_points) < 0.0:
            ordered_point_ids.reverse()
            ordered_points.reverse()
        ordered_edge_ids = _edge_ids_for_ordered_points(ordered_point_ids, edge_id_by_endpoint_pair)
        loop_rows.append(
            {
                "point_ids": ordered_point_ids,
                "edge_ids": ordered_edge_ids,
                "points": ordered_points,
                "sort_key": _component_sort_key(ordered_points),
            }
        )

    loop_rows.sort(key=lambda row: row["sort_key"])
    _validate_disjoint_simple_loops(loop_rows)
    return loop_rows


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


def _connected_components(
    participating_points: set[str],
    adjacency: dict[str, list[tuple[str, str]]],
) -> list[set[str]]:
    remaining = set(participating_points)
    components: list[set[str]] = []
    while remaining:
        start = next(iter(remaining))
        queue: deque[str] = deque([start])
        component: set[str] = set()
        while queue:
            point_id = queue.popleft()
            if point_id in component:
                continue
            component.add(point_id)
            for neighbor_id, _ in adjacency[point_id]:
                if neighbor_id not in component:
                    queue.append(neighbor_id)
        components.append(component)
        remaining -= component
    return components


def _ordered_component_point_ids(
    component: set[str],
    point_by_id: dict[str, GeometryPoint],
    adjacency: dict[str, list[tuple[str, str]]],
    edge_id_by_endpoint_pair: dict[frozenset[str], str],
    expected_edge_count: int,
) -> list[str]:
    start_point_id = min(
        component,
        key=lambda point_id: (point_by_id[point_id].x, point_by_id[point_id].y, point_id),
    )
    first_neighbor_id = min(
        (neighbor_id for neighbor_id, _ in adjacency[start_point_id]),
        key=lambda point_id: (point_by_id[point_id].x, point_by_id[point_id].y, point_id),
    )
    ordered_point_ids = [start_point_id]
    previous_point_id = start_point_id
    current_point_id = first_neighbor_id
    used_edges: set[str] = set()

    while current_point_id != start_point_id:
        ordered_point_ids.append(current_point_id)
        edge_id = edge_id_by_endpoint_pair.get(frozenset((previous_point_id, current_point_id)))
        if edge_id is None or edge_id in used_edges:
            raise ValueError("Sketch edges do not form a simple closed loop")
        used_edges.add(edge_id)
        next_candidates = [
            neighbor_id
            for neighbor_id, _ in adjacency[current_point_id]
            if neighbor_id != previous_point_id
        ]
        if len(next_candidates) != 1:
            raise ValueError("Sketch edges do not form a simple closed loop")
        previous_point_id, current_point_id = current_point_id, next_candidates[0]
        if len(ordered_point_ids) > expected_edge_count:
            raise ValueError("Sketch edges do not form a simple closed loop")

    closing_edge_id = edge_id_by_endpoint_pair.get(frozenset((previous_point_id, start_point_id)))
    if closing_edge_id is None or closing_edge_id in used_edges:
        raise ValueError("Sketch edges do not form a simple closed loop")
    used_edges.add(closing_edge_id)
    if len(used_edges) != expected_edge_count:
        raise ValueError("Only disjoint closed loops are supported")
    return ordered_point_ids


def _edge_ids_for_ordered_points(
    ordered_point_ids: list[str],
    edge_id_by_endpoint_pair: dict[frozenset[str], str],
) -> list[str]:
    ordered_edge_ids: list[str] = []
    for index, start_point_id in enumerate(ordered_point_ids):
        end_point_id = ordered_point_ids[(index + 1) % len(ordered_point_ids)]
        edge_id = edge_id_by_endpoint_pair.get(frozenset((start_point_id, end_point_id)))
        if edge_id is None:
            raise ValueError("Sketch edges do not form a simple closed loop")
        ordered_edge_ids.append(edge_id)
    return ordered_edge_ids


def _signed_area_xy(points: list[tuple[float, float]]) -> float:
    area = 0.0
    for index, point in enumerate(points):
        next_point = points[(index + 1) % len(points)]
        area += point[0] * next_point[1] - next_point[0] * point[1]
    return 0.5 * area


def _component_sort_key(points: list[tuple[float, float]]) -> tuple[float, float, float, float]:
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return (min(xs), min(ys), max(xs), max(ys))


def _validate_disjoint_simple_loops(loop_rows: list[dict[str, object]]) -> None:
    for index, loop_row in enumerate(loop_rows):
        polygon = list(loop_row["points"])
        for other_index in range(index + 1, len(loop_rows)):
            other_polygon = list(loop_rows[other_index]["points"])
            if _polygons_overlap_or_nested(polygon, other_polygon):
                raise ValueError("Overlapping, nested, or touching multi-face loops are not supported")


def _polygons_overlap_or_nested(
    polygon_a: list[tuple[float, float]],
    polygon_b: list[tuple[float, float]],
) -> bool:
    for index, point in enumerate(polygon_a):
        next_point = polygon_a[(index + 1) % len(polygon_a)]
        for other_index, other_point in enumerate(polygon_b):
            other_next_point = polygon_b[(other_index + 1) % len(polygon_b)]
            if _segments_intersect(point, next_point, other_point, other_next_point):
                return True
    return _point_in_polygon(polygon_a[0], polygon_b) or _point_in_polygon(polygon_b[0], polygon_a)


def _point_in_polygon(point: tuple[float, float], polygon: list[tuple[float, float]]) -> bool:
    inside = False
    x, y = point
    for index in range(len(polygon)):
        x1, y1 = polygon[index]
        x2, y2 = polygon[(index + 1) % len(polygon)]
        intersects = ((y1 > y) != (y2 > y)) and (
            x < (x2 - x1) * (y - y1) / max(1.0e-12, y2 - y1) + x1
        )
        if intersects:
            inside = not inside
    return inside


def _has_self_intersections(points: list[tuple[float, float]]) -> bool:
    edge_count = len(points)
    for index in range(edge_count):
        a1 = points[index]
        a2 = points[(index + 1) % edge_count]
        for other_index in range(index + 1, edge_count):
            if abs(index - other_index) == 1:
                continue
            if index == 0 and other_index == edge_count - 1:
                continue
            b1 = points[other_index]
            b2 = points[(other_index + 1) % edge_count]
            if _segments_intersect(a1, a2, b1, b2):
                return True
    return False


def _segments_intersect(
    a1: tuple[float, float],
    a2: tuple[float, float],
    b1: tuple[float, float],
    b2: tuple[float, float],
) -> bool:
    o1 = _orientation(a1, a2, b1)
    o2 = _orientation(a1, a2, b2)
    o3 = _orientation(b1, b2, a1)
    o4 = _orientation(b1, b2, a2)
    if o1 * o2 < 0.0 and o3 * o4 < 0.0:
        return True
    return (
        abs(o1) <= 1.0e-12 and _on_segment(a1, b1, a2)
        or abs(o2) <= 1.0e-12 and _on_segment(a1, b2, a2)
        or abs(o3) <= 1.0e-12 and _on_segment(b1, a1, b2)
        or abs(o4) <= 1.0e-12 and _on_segment(b1, a2, b2)
    )


def _orientation(
    a: tuple[float, float],
    b: tuple[float, float],
    c: tuple[float, float],
) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _on_segment(
    a: tuple[float, float],
    b: tuple[float, float],
    c: tuple[float, float],
) -> bool:
    return (
        min(a[0], c[0]) - 1.0e-12 <= b[0] <= max(a[0], c[0]) + 1.0e-12
        and min(a[1], c[1]) - 1.0e-12 <= b[1] <= max(a[1], c[1]) + 1.0e-12
    )

from __future__ import annotations

import math
from dataclasses import dataclass, field

from core.engineering.geometry import GeometryModel
from core.engineering.mesh_model import MeshElement, MeshModel


@dataclass(slots=True)
class MeshQualitySummary:
    node_count: int
    element_count: int
    min_area: float
    max_area: float
    avg_area: float
    min_angle: float
    max_angle: float
    degenerate_element_count: int
    warning_count: int
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class MeshCoverageSummary:
    polygon_area: float
    mesh_area: float
    relative_area_error: float
    unused_node_ids: list[int]
    missing_edge_mapping_ids: list[str]
    degenerate_element_count: int
    is_valid: bool
    warnings: list[str] = field(default_factory=list)


def calculate_triangle_area(mesh: MeshModel, element: MeshElement) -> float:
    n1, n2, n3 = [mesh.get_node_by_id(node_id) for node_id in element.node_ids]
    if n1 is None or n2 is None or n3 is None:
        raise ValueError(f"Element {element.id!r} references missing nodes")
    return 0.5 * abs((n2.x - n1.x) * (n3.y - n1.y) - (n3.x - n1.x) * (n2.y - n1.y))


def calculate_triangle_angles(mesh: MeshModel, element: MeshElement) -> list[float]:
    nodes = [mesh.get_node_by_id(node_id) for node_id in element.node_ids]
    if any(node is None for node in nodes):
        raise ValueError(f"Element {element.id!r} references missing nodes")
    a = _distance(nodes[1], nodes[2])
    b = _distance(nodes[0], nodes[2])
    c = _distance(nodes[0], nodes[1])
    return [
        _angle_from_sides(b, c, a),
        _angle_from_sides(a, c, b),
        _angle_from_sides(a, b, c),
    ]


def build_mesh_quality_summary(mesh: MeshModel) -> MeshQualitySummary:
    if not mesh.elements:
        return MeshQualitySummary(
            node_count=len(mesh.nodes),
            element_count=0,
            min_area=0.0,
            max_area=0.0,
            avg_area=0.0,
            min_angle=0.0,
            max_angle=0.0,
            degenerate_element_count=0,
            warning_count=1,
            warnings=["Mesh contains no elements"],
        )

    areas: list[float] = []
    all_angles: list[float] = []
    degenerate_count = 0

    for element in mesh.elements:
        area = calculate_triangle_area(mesh, element)
        angles = calculate_triangle_angles(mesh, element)
        areas.append(area)
        all_angles.extend(angles)
        if area <= 1.0e-12 or min(angles) <= 1.0e-6:
            degenerate_count += 1

    warnings: list[str] = []
    if degenerate_count:
        warnings.append(f"Detected {degenerate_count} degenerate elements")

    return MeshQualitySummary(
        node_count=len(mesh.nodes),
        element_count=len(mesh.elements),
        min_area=min(areas),
        max_area=max(areas),
        avg_area=sum(areas) / len(areas),
        min_angle=min(all_angles),
        max_angle=max(all_angles),
        degenerate_element_count=degenerate_count,
        warning_count=len(warnings),
        warnings=warnings,
    )


def calculate_polygon_area_from_geometry(geometry: GeometryModel) -> float:
    loops = _ordered_loop_points(geometry)
    area = 0.0
    for points in loops:
        if len(points) < 3:
            raise ValueError("Geometry polygon must contain at least 3 points")
        for index, point in enumerate(points):
            next_point = points[(index + 1) % len(points)]
            area += point[0] * next_point[1] - next_point[0] * point[1]
    return abs(area) * 0.5


def calculate_mesh_total_area(mesh: MeshModel) -> float:
    return sum(calculate_triangle_area(mesh, element) for element in mesh.elements)


def find_unused_mesh_node_ids(mesh: MeshModel) -> list[int]:
    used_node_ids: set[int] = set()
    for element in mesh.elements:
        used_node_ids.update(element.node_ids)
    return [node.id for node in mesh.nodes if node.id not in used_node_ids]


def validate_mesh_covers_geometry(
    geometry: GeometryModel,
    mesh: MeshModel,
    tolerance: float = 0.05,
) -> MeshCoverageSummary:
    if tolerance <= 0.0:
        raise ValueError("tolerance must be positive")

    polygon_area = calculate_polygon_area_from_geometry(geometry)
    if polygon_area <= 1.0e-12:
        raise ValueError("Geometry polygon area must be positive")

    mesh_area = calculate_mesh_total_area(mesh)
    unused_node_ids = find_unused_mesh_node_ids(mesh)
    degenerate_element_count = 0
    for element in mesh.elements:
        area = calculate_triangle_area(mesh, element)
        if area <= 1.0e-12:
            degenerate_element_count += 1

    geometry_edge_ids = {edge.id for edge in geometry.edges}
    missing_edge_mapping_ids = [
        edge_id
        for edge_id in sorted(geometry_edge_ids)
        if not mesh.geometry_edge_to_mesh_node_ids.get(edge_id)
        or not mesh.geometry_edge_to_mesh_element_edges.get(edge_id)
    ]

    relative_area_error = abs(mesh_area - polygon_area) / polygon_area
    warnings: list[str] = []
    if relative_area_error > tolerance:
        warnings.append(
            f"Mesh area mismatch: polygon={polygon_area:.6g}, mesh={mesh_area:.6g}, "
            f"relative_error={relative_area_error:.6g}"
        )
    if unused_node_ids:
        warnings.append(f"Unused mesh nodes: {unused_node_ids}")
    if missing_edge_mapping_ids:
        warnings.append(f"Missing geometry edge mappings: {', '.join(missing_edge_mapping_ids)}")
    if degenerate_element_count:
        warnings.append(f"Degenerate elements: {degenerate_element_count}")

    return MeshCoverageSummary(
        polygon_area=polygon_area,
        mesh_area=mesh_area,
        relative_area_error=relative_area_error,
        unused_node_ids=unused_node_ids,
        missing_edge_mapping_ids=missing_edge_mapping_ids,
        degenerate_element_count=degenerate_element_count,
        is_valid=not warnings,
        warnings=warnings,
    )


def _ordered_loop_points(geometry: GeometryModel) -> list[list[tuple[float, float]]]:
    face_rows = geometry.faces or []
    point_by_id = {point.id: point for point in geometry.points}
    edge_by_id = {edge.id: edge for edge in geometry.edges}
    if not face_rows:
        raise ValueError("Geometry contains no closed loop")
    loop_points: list[list[tuple[float, float]]] = []
    for face in face_rows:
        edges = [edge_by_id[edge_id] for edge_id in face.edge_ids]
        adjacency: dict[str, list[str]] = {}
        for edge in edges:
            if edge.start_point_id not in point_by_id or edge.end_point_id not in point_by_id:
                raise ValueError("Geometry edge references unknown points")
            adjacency.setdefault(edge.start_point_id, []).append(edge.end_point_id)
            adjacency.setdefault(edge.end_point_id, []).append(edge.start_point_id)
        if any(len(neighbors) != 2 for neighbors in adjacency.values()):
            raise ValueError("Geometry edges do not form a single closed loop")

        start_id = min(adjacency, key=lambda point_id: (point_by_id[point_id].x, point_by_id[point_id].y, point_id))
        current_id = adjacency[start_id][0]
        previous_id = start_id
        ordered_ids = [start_id]

        while current_id != start_id:
            ordered_ids.append(current_id)
            next_candidates = [item for item in adjacency[current_id] if item != previous_id]
            if len(next_candidates) != 1:
                raise ValueError("Geometry edges do not form a single closed loop")
            previous_id, current_id = current_id, next_candidates[0]
            if len(ordered_ids) > len(adjacency) + 1:
                raise ValueError("Geometry edges do not form a single closed loop")

        ordered_points = [(point_by_id[point_id].x, point_by_id[point_id].y) for point_id in ordered_ids]
        if _signed_area_xy(ordered_points) < 0.0:
            ordered_points.reverse()
        loop_points.append(ordered_points)
    return loop_points


def _signed_area_xy(points: list[tuple[float, float]]) -> float:
    area = 0.0
    for index, point in enumerate(points):
        next_point = points[(index + 1) % len(points)]
        area += point[0] * next_point[1] - next_point[0] * point[1]
    return 0.5 * area


def _distance(a, b) -> float:
    return math.hypot(b.x - a.x, b.y - a.y)


def _angle_from_sides(side_a: float, side_b: float, opposite_side: float) -> float:
    denominator = max(2.0 * side_a * side_b, 1.0e-12)
    cosine = (side_a**2 + side_b**2 - opposite_side**2) / denominator
    cosine = min(1.0, max(-1.0, cosine))
    return math.degrees(math.acos(cosine))

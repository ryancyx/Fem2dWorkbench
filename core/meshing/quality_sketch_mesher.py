from __future__ import annotations

from dataclasses import dataclass

from core.engineering.geometry import GeometryModel
from core.engineering.mesh_model import MeshModel


_EPS = 1.0e-12


@dataclass(frozen=True)
class BoundaryLoop:
    ordered_point_ids: list[str]
    ordered_edge_ids: list[str]
    ordered_points: list[tuple[float, float]]
    face_id: str


def generate_quality_sketch_tri_mesh(
    geometry: GeometryModel,
    target_size: float = 0.2,
    max_area: float | None = None,
    min_angle: float = 25.0,
) -> MeshModel:
    if target_size <= 0.0:
        raise ValueError("target_size must be positive")
    if max_area is not None and max_area <= 0.0:
        raise ValueError("max_area must be positive when provided")
    if min_angle <= 0.0 or min_angle >= 180.0:
        raise ValueError("min_angle must be between 0 and 180")

    from core.meshing.gmsh_cst_mesher import generate_gmsh_cst_mesh

    return generate_gmsh_cst_mesh(
        geometry=geometry,
        target_size=target_size,
        max_area=max_area,
        min_angle=min_angle,
    )


def _reconstruct_boundary_loop_from_edges(geometry: GeometryModel) -> BoundaryLoop:
    loops = _reconstruct_boundary_loops_from_geometry(geometry)
    if len(loops) != 1:
        raise ValueError("Quality sketch mesher requires exactly one face")
    return loops[0]


def _reconstruct_boundary_loops_from_geometry(geometry: GeometryModel) -> list[BoundaryLoop]:
    if len(geometry.points) < 3:
        raise ValueError("Geometry must contain at least 3 points")
    if len(geometry.edges) < 3:
        raise ValueError("Geometry must contain at least 3 edges")

    point_by_id = {point.id: point for point in geometry.points}
    edge_by_id = {edge.id: edge for edge in geometry.edges}
    face_rows = geometry.faces or [
        type("_FaceRow", (), {"id": f"f{index}", "edge_ids": list(component_edge_ids)})
        for index, component_edge_ids in enumerate(_edge_components(geometry), start=1)
    ]
    loops: list[BoundaryLoop] = []
    for face in face_rows:
        try:
            candidate_edges = [edge_by_id[edge_id] for edge_id in face.edge_ids]
        except KeyError as exc:
            raise ValueError(f"Geometry face references unknown edge {exc.args[0]!r}") from exc
        loops.append(_reconstruct_single_boundary_loop(point_by_id, candidate_edges, face.id))
    return loops


def _reconstruct_single_boundary_loop(
    point_by_id: dict[str, object],
    candidate_edges: list[object],
    face_id: str,
) -> BoundaryLoop:
    adjacency: dict[str, list[tuple[str, str]]] = {}
    edge_id_by_endpoint_pair: dict[frozenset[str], str] = {}
    participating_point_ids: set[str] = set()
    for edge in candidate_edges:
        if edge.start_point_id not in point_by_id or edge.end_point_id not in point_by_id:
            raise ValueError(f"Geometry edge {edge.id!r} references unknown points")
        endpoint_pair = frozenset((edge.start_point_id, edge.end_point_id))
        if endpoint_pair in edge_id_by_endpoint_pair:
            raise ValueError("Geometry contains duplicate edges between the same points")
        edge_id_by_endpoint_pair[endpoint_pair] = edge.id
        participating_point_ids.add(edge.start_point_id)
        participating_point_ids.add(edge.end_point_id)
        adjacency.setdefault(edge.start_point_id, []).append((edge.end_point_id, edge.id))
        adjacency.setdefault(edge.end_point_id, []).append((edge.start_point_id, edge.id))

    if len(participating_point_ids) < 3:
        raise ValueError("Geometry loop must contain at least 3 participating points")
    if set(adjacency) != participating_point_ids:
        raise ValueError("Geometry edges do not form a single closed loop")
    if any(len(neighbors) != 2 for neighbors in adjacency.values()):
        raise ValueError("Geometry edges do not form a single closed loop")

    start_point_id = min(
        participating_point_ids,
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
        if edge_id is None:
            raise ValueError("Geometry edges do not form a single closed loop")
        if edge_id in used_edges:
            raise ValueError("Geometry contains disconnected or multiple loops")
        used_edges.add(edge_id)

        next_candidates = [
            (neighbor_id, next_edge_id)
            for neighbor_id, next_edge_id in adjacency[current_point_id]
            if neighbor_id != previous_point_id
        ]
        if len(next_candidates) != 1:
            raise ValueError("Geometry edges do not form a single closed loop")
        previous_point_id, current_point_id = current_point_id, next_candidates[0][0]
        if len(ordered_point_ids) > len(candidate_edges):
            raise ValueError("Geometry contains disconnected or multiple loops")

    closing_edge_id = edge_id_by_endpoint_pair.get(frozenset((previous_point_id, start_point_id)))
    if closing_edge_id is None or closing_edge_id in used_edges:
        raise ValueError("Geometry edges do not form a single closed loop")
    used_edges.add(closing_edge_id)

    if len(ordered_point_ids) != len(participating_point_ids) or len(used_edges) != len(candidate_edges):
        raise ValueError("Geometry contains disconnected or multiple loops")

    ordered_points = [_xy(point_by_id[point_id]) for point_id in ordered_point_ids]
    signed_area = _signed_area(ordered_points)
    if abs(signed_area) <= _EPS:
        raise ValueError("Geometry loop area must be positive")
    if _has_self_intersections(ordered_points):
        raise ValueError("Geometry loop appears to be self-intersecting")
    if signed_area < 0.0:
        ordered_point_ids.reverse()
        ordered_points.reverse()

    ordered_edge_ids = _edge_ids_for_ordered_points(ordered_point_ids, edge_id_by_endpoint_pair)
    return BoundaryLoop(
        ordered_point_ids=ordered_point_ids,
        ordered_edge_ids=ordered_edge_ids,
        ordered_points=ordered_points,
        face_id=face_id,
    )


def _edge_components(geometry: GeometryModel) -> list[list[str]]:
    point_neighbors: dict[str, set[str]] = {}
    for edge in geometry.edges:
        point_neighbors.setdefault(edge.start_point_id, set()).add(edge.end_point_id)
        point_neighbors.setdefault(edge.end_point_id, set()).add(edge.start_point_id)
    remaining = set(point_neighbors)
    components: list[list[str]] = []
    edge_ids_by_component: list[list[str]] = []
    while remaining:
        start = next(iter(remaining))
        stack = [start]
        component_points: set[str] = set()
        while stack:
            point_id = stack.pop()
            if point_id in component_points:
                continue
            component_points.add(point_id)
            stack.extend(point_neighbors.get(point_id, set()) - component_points)
        remaining -= component_points
        edge_ids_by_component.append(
            [
                edge.id
                for edge in geometry.edges
                if edge.start_point_id in component_points and edge.end_point_id in component_points
            ]
        )
    return edge_ids_by_component


def _edge_ids_for_ordered_points(
    ordered_point_ids: list[str],
    edge_id_by_endpoint_pair: dict[frozenset[str], str],
) -> list[str]:
    ordered_edge_ids: list[str] = []
    for index, start_point_id in enumerate(ordered_point_ids):
        end_point_id = ordered_point_ids[(index + 1) % len(ordered_point_ids)]
        edge_id = edge_id_by_endpoint_pair.get(frozenset((start_point_id, end_point_id)))
        if edge_id is None:
            raise ValueError("Geometry edges do not form a single closed loop")
        ordered_edge_ids.append(edge_id)
    return ordered_edge_ids


def _xy(point) -> tuple[float, float]:
    return float(point.x), float(point.y)


def _signed_area(points: list[tuple[float, float]]) -> float:
    area = 0.0
    for index, point in enumerate(points):
        next_point = points[(index + 1) % len(points)]
        area += point[0] * next_point[1] - next_point[0] * point[1]
    return 0.5 * area


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
    if o1 * o2 < -_EPS and o3 * o4 < -_EPS:
        return True
    return (
        abs(o1) <= _EPS and _on_segment(a1, b1, a2)
        or abs(o2) <= _EPS and _on_segment(a1, b2, a2)
        or abs(o3) <= _EPS and _on_segment(b1, a1, b2)
        or abs(o4) <= _EPS and _on_segment(b1, a2, b2)
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
        min(a[0], c[0]) - _EPS <= b[0] <= max(a[0], c[0]) + _EPS
        and min(a[1], c[1]) - _EPS <= b[1] <= max(a[1], c[1]) + _EPS
    )

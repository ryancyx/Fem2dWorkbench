from __future__ import annotations

from dataclasses import dataclass

from core.engineering.geometry import GeometryEdge, GeometryModel, GeometryPoint
from core.engineering.mesh_model import MeshElement, MeshModel, MeshNode


_EPS = 1.0e-12


@dataclass(frozen=True)
class _OrderedPolygon:
    face_id: str
    point_ids: list[str]
    points: list[GeometryPoint]
    edge_ids: list[str]


def generate_sketch_tri_mesh(geometry: GeometryModel) -> MeshModel:
    """
    Generate a CST triangular mesh from a single closed sketch face.

    Current scope of stage 13B:
    - one closed face
    - no holes
    - no self-intersection handling
    - triangulation by ear clipping
    - boundary edge mapping preserved

    The generated mesh uses the sketch vertices directly as mesh nodes.
    No interior refinement is performed in this stage.
    """
    polygon = _extract_ordered_polygon(geometry)

    if len(polygon.points) < 3:
        raise ValueError("Sketch polygon must contain at least 3 points")

    points = list(polygon.points)
    point_ids = list(polygon.point_ids)

    if _signed_area(points) < 0.0:
        points.reverse()
        point_ids.reverse()

    if abs(_signed_area(points)) <= _EPS:
        raise ValueError("Sketch polygon area must be positive")

    nodes = [
        MeshNode(
            id=index + 1,
            x=point.x,
            y=point.y,
        )
        for index, point in enumerate(points)
    ]

    point_id_to_node_id = {
        point_id: index + 1
        for index, point_id in enumerate(point_ids)
    }

    triangles = _ear_clip(points)

    elements = [
        MeshElement(
            id=index + 1,
            node_ids=[
                triangle[0] + 1,
                triangle[1] + 1,
                triangle[2] + 1,
            ],
            source_face_id=polygon.face_id,
        )
        for index, triangle in enumerate(triangles)
    ]

    mesh = MeshModel(
        nodes=nodes,
        elements=elements,
        geometry_point_to_mesh_node_ids={
            point_id: [node_id]
            for point_id, node_id in point_id_to_node_id.items()
        },
        geometry_edge_to_mesh_node_ids=_build_edge_to_mesh_node_ids(
            geometry,
            point_id_to_node_id,
        ),
        geometry_edge_to_mesh_element_edges=_build_edge_to_mesh_element_edges(
            geometry,
            elements,
            point_id_to_node_id,
        ),
    )

    _validate_positive_element_areas(mesh)

    return mesh


def _extract_ordered_polygon(geometry: GeometryModel) -> _OrderedPolygon:
    if len(geometry.faces) != 1:
        raise ValueError("Sketch mesher requires exactly one face")
    if len(geometry.points) < 3:
        raise ValueError("Sketch mesher requires at least 3 points")
    if len(geometry.edges) < 3:
        raise ValueError("Sketch mesher requires at least 3 edges")

    face = geometry.faces[0]
    point_by_id = {point.id: point for point in geometry.points}
    edge_by_id = {edge.id: edge for edge in geometry.edges}

    missing_edges = [edge_id for edge_id in face.edge_ids if edge_id not in edge_by_id]
    if missing_edges:
        raise ValueError(f"Sketch face references unknown edges: {missing_edges}")

    face_edges = [edge_by_id[edge_id] for edge_id in face.edge_ids]

    for edge in face_edges:
        if edge.start_point_id not in point_by_id or edge.end_point_id not in point_by_id:
            raise ValueError(f"Sketch edge {edge.id!r} references unknown points")

    participating_point_ids = _collect_participating_point_ids(face_edges)

    if len(participating_point_ids) < 3:
        raise ValueError("Sketch face must contain at least 3 participating points")

    _validate_single_closed_loop(face_edges, participating_point_ids)

    ordered_point_ids = _order_loop_point_ids(face_edges, participating_point_ids)
    ordered_points = [point_by_id[point_id] for point_id in ordered_point_ids]

    return _OrderedPolygon(
        face_id=face.id,
        point_ids=ordered_point_ids,
        points=ordered_points,
        edge_ids=list(face.edge_ids),
    )


def _collect_participating_point_ids(edges: list[GeometryEdge]) -> set[str]:
    point_ids: set[str] = set()
    for edge in edges:
        point_ids.add(edge.start_point_id)
        point_ids.add(edge.end_point_id)
    return point_ids


def _validate_single_closed_loop(
    edges: list[GeometryEdge],
    participating_point_ids: set[str],
) -> None:
    degree = {point_id: 0 for point_id in participating_point_ids}
    adjacency = {point_id: set() for point_id in participating_point_ids}

    for edge in edges:
        degree[edge.start_point_id] += 1
        degree[edge.end_point_id] += 1
        adjacency[edge.start_point_id].add(edge.end_point_id)
        adjacency[edge.end_point_id].add(edge.start_point_id)

    bad_degree_points = [
        point_id
        for point_id, value in degree.items()
        if value != 2
    ]
    if bad_degree_points:
        raise ValueError(
            "Sketch face edges must form a single closed loop; "
            f"points with invalid degree: {bad_degree_points}"
        )

    visited = set()
    stack = [next(iter(participating_point_ids))]

    while stack:
        point_id = stack.pop()
        if point_id in visited:
            continue
        visited.add(point_id)
        stack.extend(adjacency[point_id] - visited)

    if visited != participating_point_ids:
        raise ValueError("Sketch face edges must form one connected closed loop")


def _order_loop_point_ids(
    edges: list[GeometryEdge],
    participating_point_ids: set[str],
) -> list[str]:
    adjacency: dict[str, list[tuple[str, str]]] = {
        point_id: []
        for point_id in participating_point_ids
    }

    for edge in edges:
        adjacency[edge.start_point_id].append((edge.end_point_id, edge.id))
        adjacency[edge.end_point_id].append((edge.start_point_id, edge.id))

    first_edge = edges[0]
    start_point_id = first_edge.start_point_id
    current_point_id = first_edge.end_point_id

    ordered_point_ids = [start_point_id, current_point_id]
    used_edge_ids = {first_edge.id}

    while True:
        candidates = [
            (neighbor_id, edge_id)
            for neighbor_id, edge_id in adjacency[current_point_id]
            if edge_id not in used_edge_ids
        ]

        if not candidates:
            if len(used_edge_ids) == len(edges):
                return ordered_point_ids
            raise ValueError("Sketch face loop ordering failed")

        next_point_id, edge_id = candidates[0]
        used_edge_ids.add(edge_id)

        if next_point_id == start_point_id:
            if len(used_edge_ids) != len(edges):
                raise ValueError("Sketch face loop closes before using all edges")
            return ordered_point_ids

        if next_point_id in ordered_point_ids:
            raise ValueError("Sketch face loop self-revisits a point")

        ordered_point_ids.append(next_point_id)
        current_point_id = next_point_id


def _ear_clip(points: list[GeometryPoint]) -> list[list[int]]:
    if len(points) < 3:
        raise ValueError("At least 3 points are required for triangulation")

    remaining = list(range(len(points)))
    triangles: list[list[int]] = []

    guard = 0
    max_guard = len(points) * len(points)

    while len(remaining) > 3:
        guard += 1
        if guard > max_guard:
            raise ValueError("Sketch polygon triangulation failed")

        ear_found = False

        for local_index in range(len(remaining)):
            previous_index = remaining[local_index - 1]
            current_index = remaining[local_index]
            next_index = remaining[(local_index + 1) % len(remaining)]

            if not _is_convex_vertex(
                points[previous_index],
                points[current_index],
                points[next_index],
            ):
                continue

            if _contains_other_point_in_triangle(
                points,
                remaining,
                previous_index,
                current_index,
                next_index,
            ):
                continue

            triangles.append([previous_index, current_index, next_index])
            del remaining[local_index]
            ear_found = True
            break

        if not ear_found:
            raise ValueError(
                "Sketch polygon triangulation failed; "
                "the polygon may be self-intersecting or degenerate"
            )

    triangles.append([remaining[0], remaining[1], remaining[2]])

    return triangles


def _is_convex_vertex(
    previous_point: GeometryPoint,
    current_point: GeometryPoint,
    next_point: GeometryPoint,
) -> bool:
    return _cross(previous_point, current_point, next_point) > _EPS


def _contains_other_point_in_triangle(
    points: list[GeometryPoint],
    remaining_indices: list[int],
    previous_index: int,
    current_index: int,
    next_index: int,
) -> bool:
    a = points[previous_index]
    b = points[current_index]
    c = points[next_index]

    for point_index in remaining_indices:
        if point_index in {previous_index, current_index, next_index}:
            continue
        if _point_in_triangle(points[point_index], a, b, c):
            return True

    return False


def _point_in_triangle(
    point: GeometryPoint,
    a: GeometryPoint,
    b: GeometryPoint,
    c: GeometryPoint,
) -> bool:
    area_1 = _cross(point, a, b)
    area_2 = _cross(point, b, c)
    area_3 = _cross(point, c, a)

    has_negative = area_1 < -_EPS or area_2 < -_EPS or area_3 < -_EPS
    has_positive = area_1 > _EPS or area_2 > _EPS or area_3 > _EPS

    return not (has_negative and has_positive)


def _signed_area(points: list[GeometryPoint]) -> float:
    area = 0.0

    for index, point in enumerate(points):
        next_point = points[(index + 1) % len(points)]
        area += point.x * next_point.y - next_point.x * point.y

    return 0.5 * area


def _cross(
    a: GeometryPoint,
    b: GeometryPoint,
    c: GeometryPoint,
) -> float:
    return (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)


def _build_edge_to_mesh_node_ids(
    geometry: GeometryModel,
    point_id_to_node_id: dict[str, int],
) -> dict[str, list[int]]:
    mapping: dict[str, list[int]] = {}

    for edge in geometry.edges:
        if edge.start_point_id not in point_id_to_node_id:
            continue
        if edge.end_point_id not in point_id_to_node_id:
            continue

        mapping[edge.id] = [
            point_id_to_node_id[edge.start_point_id],
            point_id_to_node_id[edge.end_point_id],
        ]

    return mapping


def _build_edge_to_mesh_element_edges(
    geometry: GeometryModel,
    elements: list[MeshElement],
    point_id_to_node_id: dict[str, int],
) -> dict[str, list[tuple[int, int, int]]]:
    mapping: dict[str, list[tuple[int, int, int]]] = {}

    for edge in geometry.edges:
        if edge.start_point_id not in point_id_to_node_id:
            continue
        if edge.end_point_id not in point_id_to_node_id:
            continue

        start_node_id = point_id_to_node_id[edge.start_point_id]
        end_node_id = point_id_to_node_id[edge.end_point_id]
        edge_node_set = {start_node_id, end_node_id}

        matched_edges: list[tuple[int, int, int]] = []

        for element in elements:
            element_node_set = set(element.node_ids)
            if not edge_node_set.issubset(element_node_set):
                continue

            local_a = element.node_ids.index(start_node_id)
            local_b = element.node_ids.index(end_node_id)
            matched_edges.append((element.id, local_a, local_b))

        if not matched_edges:
            raise ValueError(f"Could not map geometry edge {edge.id!r} to a mesh element edge")

        mapping[edge.id] = matched_edges

    return mapping


def _validate_positive_element_areas(mesh: MeshModel) -> None:
    for element in mesh.elements:
        n1 = mesh.get_node_by_id(element.node_ids[0])
        n2 = mesh.get_node_by_id(element.node_ids[1])
        n3 = mesh.get_node_by_id(element.node_ids[2])

        if n1 is None or n2 is None or n3 is None:
            raise ValueError(f"MeshElement {element.id!r} references missing nodes")

        area = 0.5 * (
            (n2.x - n1.x) * (n3.y - n1.y)
            - (n3.x - n1.x) * (n2.y - n1.y)
        )

        if area <= _EPS:
            raise ValueError(f"MeshElement {element.id!r} has non-positive area")

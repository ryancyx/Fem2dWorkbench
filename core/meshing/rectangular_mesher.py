from __future__ import annotations

from core.engineering.geometry import GeometryModel
from core.engineering.mesh_model import MeshElement, MeshModel, MeshNode


def generate_rectangular_tri_mesh(
    geometry: GeometryModel,
    nx: int,
    ny: int,
) -> MeshModel:
    if not isinstance(nx, int) or nx <= 0:
        raise ValueError("nx must be a positive integer")
    if not isinstance(ny, int) or ny <= 0:
        raise ValueError("ny must be a positive integer")

    min_x, min_y, max_x, max_y = _extract_rectangle_bounds(geometry)
    width = max_x - min_x
    height = max_y - min_y
    face_id = geometry.faces[0].id

    nodes = [
        MeshNode(
            id=row * (nx + 1) + col + 1,
            x=min_x + width * col / nx,
            y=min_y + height * row / ny,
        )
        for row in range(ny + 1)
        for col in range(nx + 1)
    ]

    elements: list[MeshElement] = []
    geometry_edge_to_mesh_element_edges = {
        "bottom": [],
        "right": [],
        "top": [],
        "left": [],
    }

    element_id = 1
    for row in range(ny):
        for col in range(nx):
            n00 = _node_id(row, col, nx)
            n10 = _node_id(row, col + 1, nx)
            n01 = _node_id(row + 1, col, nx)
            n11 = _node_id(row + 1, col + 1, nx)

            triangle_1_id = element_id
            elements.append(
                MeshElement(
                    id=triangle_1_id,
                    node_ids=[n00, n10, n11],
                    source_face_id=face_id,
                )
            )
            element_id += 1

            triangle_2_id = element_id
            elements.append(
                MeshElement(
                    id=triangle_2_id,
                    node_ids=[n00, n11, n01],
                    source_face_id=face_id,
                )
            )
            element_id += 1

            if row == 0:
                geometry_edge_to_mesh_element_edges["bottom"].append((triangle_1_id, 0, 1))
            if col == nx - 1:
                geometry_edge_to_mesh_element_edges["right"].append((triangle_1_id, 1, 2))
            if row == ny - 1:
                geometry_edge_to_mesh_element_edges["top"].append((triangle_2_id, 1, 2))
            if col == 0:
                geometry_edge_to_mesh_element_edges["left"].append((triangle_2_id, 2, 0))

    geometry_edge_to_mesh_node_ids = {
        "bottom": [_node_id(0, col, nx) for col in range(nx + 1)],
        "right": [_node_id(row, nx, nx) for row in range(ny + 1)],
        "top": [_node_id(ny, col, nx) for col in range(nx + 1)],
        "left": [_node_id(row, 0, nx) for row in range(ny + 1)],
    }

    geometry_point_to_mesh_node_ids = {
        "p1": [_node_id(0, 0, nx)],
        "p2": [_node_id(0, nx, nx)],
        "p3": [_node_id(ny, nx, nx)],
        "p4": [_node_id(ny, 0, nx)],
    }

    return MeshModel(
        nodes=nodes,
        elements=elements,
        geometry_point_to_mesh_node_ids=geometry_point_to_mesh_node_ids,
        geometry_edge_to_mesh_node_ids=geometry_edge_to_mesh_node_ids,
        geometry_edge_to_mesh_element_edges=geometry_edge_to_mesh_element_edges,
    )


def _node_id(row: int, col: int, nx: int) -> int:
    return row * (nx + 1) + col + 1


def _extract_rectangle_bounds(geometry: GeometryModel) -> tuple[float, float, float, float]:
    required_edges = {"bottom", "right", "top", "left"}
    edge_ids = {edge.id for edge in geometry.edges}
    if edge_ids != required_edges:
        raise ValueError("geometry must contain exactly bottom, right, top, and left edges")
    if len(geometry.points) != 4 or len(geometry.faces) != 1:
        raise ValueError("geometry must be a single rectangular face with 4 points")

    point_by_id = {point.id: point for point in geometry.points}
    edge_by_id = {edge.id: edge for edge in geometry.edges}
    for edge in geometry.edges:
        if edge.start_point_id not in point_by_id or edge.end_point_id not in point_by_id:
            raise ValueError(f"Geometry edge {edge.id!r} references unknown points")

    bottom_start = point_by_id[edge_by_id["bottom"].start_point_id]
    bottom_end = point_by_id[edge_by_id["bottom"].end_point_id]
    right_start = point_by_id[edge_by_id["right"].start_point_id]
    right_end = point_by_id[edge_by_id["right"].end_point_id]
    top_start = point_by_id[edge_by_id["top"].start_point_id]
    top_end = point_by_id[edge_by_id["top"].end_point_id]
    left_start = point_by_id[edge_by_id["left"].start_point_id]
    left_end = point_by_id[edge_by_id["left"].end_point_id]

    if bottom_start.id != left_end.id or bottom_end.id != right_start.id:
        raise ValueError("geometry edge connectivity does not match create_rectangle output")
    if right_end.id != top_start.id or top_end.id != left_start.id:
        raise ValueError("geometry edge connectivity does not match create_rectangle output")

    xs = {point.x for point in geometry.points}
    ys = {point.y for point in geometry.points}
    if len(xs) != 2 or len(ys) != 2:
        raise ValueError("geometry points must form an axis-aligned rectangle")

    min_x = min(xs)
    max_x = max(xs)
    min_y = min(ys)
    max_y = max(ys)
    if min_x >= max_x or min_y >= max_y:
        raise ValueError("geometry rectangle dimensions must be positive")

    expected_corners = {
        (min_x, min_y),
        (max_x, min_y),
        (max_x, max_y),
        (min_x, max_y),
    }
    actual_corners = {(point.x, point.y) for point in geometry.points}
    if actual_corners != expected_corners:
        raise ValueError("geometry points must match rectangle corner coordinates")

    return min_x, min_y, max_x, max_y

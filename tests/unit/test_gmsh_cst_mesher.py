from __future__ import annotations

from core.engineering.geometry import GeometryModel
from core.meshing.gmsh_cst_mesher import generate_gmsh_cst_mesh
from services.mesh_quality_service import calculate_triangle_area, validate_mesh_covers_geometry
from services.sketch_geometry_service import create_geometry_from_polygon_points


def _assert_valid_gmsh_mesh(geometry: GeometryModel, target_size: float = 0.25) -> None:
    mesh = generate_gmsh_cst_mesh(geometry, target_size=target_size, min_angle=25.0)
    coverage = validate_mesh_covers_geometry(geometry, mesh, tolerance=0.03)
    used_node_ids = {node_id for element in mesh.elements for node_id in element.node_ids}

    assert mesh.metadata["mesh_type"] == "gmsh_cst"
    assert mesh.metadata["mesher_backend"] == "gmsh"
    assert all(element.element_type == "CST" for element in mesh.elements)
    assert all(len(element.node_ids) == 3 for element in mesh.elements)
    assert coverage.is_valid is True
    assert coverage.relative_area_error < 0.03
    assert coverage.unused_node_ids == []
    assert coverage.degenerate_element_count == 0
    assert set(mesh.geometry_point_to_mesh_node_ids) == {point.id for point in geometry.points}
    assert set(mesh.geometry_edge_to_mesh_node_ids) == {edge.id for edge in geometry.edges}
    assert set(mesh.geometry_edge_to_mesh_element_edges) == {edge.id for edge in geometry.edges}
    assert all(mesh.geometry_edge_to_mesh_node_ids[edge.id] for edge in geometry.edges)
    assert all(mesh.geometry_edge_to_mesh_element_edges[edge.id] for edge in geometry.edges)
    assert used_node_ids == {node.id for node in mesh.nodes}
    assert all(calculate_triangle_area(mesh, element) > 1.0e-12 for element in mesh.elements)


def test_rectangle_gmsh_cst_mesh():
    geometry = create_geometry_from_polygon_points(
        [(0.0, 0.0), (2.0, 0.0), (2.0, 1.0), (0.0, 1.0)]
    )

    _assert_valid_gmsh_mesh(geometry)


def test_trapezoid_gmsh_cst_mesh():
    geometry = create_geometry_from_polygon_points(
        [(0.0, 0.0), (2.4, 0.0), (1.8, 1.0), (0.4, 1.0)]
    )

    _assert_valid_gmsh_mesh(geometry)


def test_pentagon_gmsh_cst_mesh():
    geometry = create_geometry_from_polygon_points(
        [(0.0, 0.0), (2.0, 0.0), (2.4, 0.8), (1.1, 1.6), (-0.2, 0.9)]
    )

    _assert_valid_gmsh_mesh(geometry)


def test_reversed_orientation_gmsh_cst_mesh():
    geometry = create_geometry_from_polygon_points(
        [(0.0, 0.0), (0.0, 1.0), (2.0, 1.0), (2.0, 0.0)]
    )

    _assert_valid_gmsh_mesh(geometry)


def test_random_point_and_edge_storage_order_gmsh_cst_mesh():
    geometry = create_geometry_from_polygon_points(
        [(0.0, 0.0), (2.0, 0.0), (2.0, 1.0), (0.0, 1.0)]
    )
    geometry.points = [geometry.points[2], geometry.points[0], geometry.points[3], geometry.points[1]]
    geometry.edges = [geometry.edges[2], geometry.edges[0], geometry.edges[3], geometry.edges[1]]
    geometry.faces[0].edge_ids = ["e3", "e1", "e4", "e2"]

    _assert_valid_gmsh_mesh(geometry)

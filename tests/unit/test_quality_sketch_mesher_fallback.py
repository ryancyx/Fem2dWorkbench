from __future__ import annotations

from core.meshing.quality_sketch_mesher import generate_quality_sketch_tri_mesh
from services.mesh_quality_service import build_mesh_quality_summary, validate_mesh_covers_geometry
from services.sketch_geometry_service import create_geometry_from_polygon_points


def _quad_geometry():
    return create_geometry_from_polygon_points(
        [(0.0, 0.0), (2.0, 0.0), (2.0, 1.0), (0.0, 1.0)]
    )


def _concave_geometry():
    return create_geometry_from_polygon_points(
        [(0.0, 0.0), (2.0, 0.0), (2.0, 0.6), (1.2, 0.6), (1.2, 1.2), (0.0, 1.2)]
    )


def _assert_boundary_mappings(mesh, edge_ids, point_ids):
    assert set(mesh.geometry_edge_to_mesh_node_ids) == set(edge_ids)
    assert set(mesh.geometry_edge_to_mesh_element_edges) == set(edge_ids)
    assert all(mesh.geometry_edge_to_mesh_node_ids[edge_id] for edge_id in edge_ids)
    assert all(mesh.geometry_edge_to_mesh_element_edges[edge_id] for edge_id in edge_ids)
    assert set(mesh.geometry_point_to_mesh_node_ids) == set(point_ids)
    assert all(mesh.geometry_point_to_mesh_node_ids[point_id] for point_id in point_ids)


def test_quality_mesher_uses_gmsh_primary_path():
    mesh = generate_quality_sketch_tri_mesh(_quad_geometry(), target_size=0.25, min_angle=25.0)

    assert len(mesh.nodes) > 4
    assert len(mesh.elements) > 2
    assert mesh.metadata["mesh_type"] == "gmsh_cst"
    assert mesh.metadata["mesher_backend"] == "gmsh"
    _assert_boundary_mappings(mesh, ("e1", "e2", "e3", "e4"), ("p1", "p2", "p3", "p4"))
    coverage = validate_mesh_covers_geometry(_quad_geometry(), mesh, tolerance=0.03)
    assert coverage.is_valid is True


def test_quality_gmsh_mesh_handles_concave_polygon():
    mesh = generate_quality_sketch_tri_mesh(_concave_geometry(), target_size=0.2, min_angle=25.0)

    assert len(mesh.nodes) > 6
    assert len(mesh.elements) > 4
    _assert_boundary_mappings(
        mesh,
        ("e1", "e2", "e3", "e4", "e5", "e6"),
        ("p1", "p2", "p3", "p4", "p5", "p6"),
    )


def test_quality_gmsh_mesh_still_has_valid_quality_summary():
    mesh = generate_quality_sketch_tri_mesh(_quad_geometry(), target_size=0.25, min_angle=25.0)
    summary = build_mesh_quality_summary(mesh)

    assert summary.node_count == len(mesh.nodes)
    assert summary.element_count == len(mesh.elements)
    assert summary.min_area > 0.0
    assert summary.min_angle > 0.0
    assert summary.degenerate_element_count == 0

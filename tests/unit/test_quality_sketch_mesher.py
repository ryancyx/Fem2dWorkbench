from __future__ import annotations

from core.meshing.quality_sketch_mesher import generate_quality_sketch_tri_mesh
from services.mesh_quality_service import build_mesh_quality_summary
from services.sketch_geometry_service import create_geometry_from_polygon_points


def _quad_geometry():
    return create_geometry_from_polygon_points(
        [(0.0, 0.0), (2.0, 0.0), (2.0, 1.0), (0.0, 1.0)]
    )


def test_quality_mesher_generates_gmsh_cst_mesh_and_mappings():
    mesh = generate_quality_sketch_tri_mesh(_quad_geometry(), target_size=0.25, min_angle=25.0)

    assert len(mesh.nodes) > 4
    assert len(mesh.elements) > 2
    assert mesh.metadata["mesh_type"] == "gmsh_cst"
    assert mesh.metadata["mesher_backend"] == "gmsh"
    assert set(mesh.geometry_edge_to_mesh_node_ids) == {"e1", "e2", "e3", "e4"}
    assert set(mesh.geometry_edge_to_mesh_element_edges) == {"e1", "e2", "e3", "e4"}
    assert all(mesh.geometry_edge_to_mesh_node_ids[edge_id] for edge_id in ("e1", "e2", "e3", "e4"))
    assert all(mesh.geometry_edge_to_mesh_element_edges[edge_id] for edge_id in ("e1", "e2", "e3", "e4"))
    assert set(mesh.geometry_point_to_mesh_node_ids) == {"p1", "p2", "p3", "p4"}
    assert all(mesh.geometry_point_to_mesh_node_ids[point_id] for point_id in ("p1", "p2", "p3", "p4"))


def test_quality_mesher_refines_when_target_size_decreases():
    coarse = generate_quality_sketch_tri_mesh(_quad_geometry(), target_size=0.5, min_angle=25.0)
    fine = generate_quality_sketch_tri_mesh(_quad_geometry(), target_size=0.2, min_angle=25.0)

    assert len(fine.nodes) > len(coarse.nodes)
    assert len(fine.elements) > len(coarse.elements)


def test_quality_summary_reports_angles_areas_and_no_degenerate_elements():
    mesh = generate_quality_sketch_tri_mesh(_quad_geometry(), target_size=0.25, min_angle=25.0)
    summary = build_mesh_quality_summary(mesh)

    assert summary.node_count == len(mesh.nodes)
    assert summary.element_count == len(mesh.elements)
    assert summary.min_area > 0.0
    assert summary.max_area >= summary.min_area
    assert summary.min_angle > 0.0
    assert summary.max_angle >= summary.min_angle
    assert summary.degenerate_element_count == 0

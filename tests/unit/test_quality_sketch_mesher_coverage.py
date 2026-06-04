from __future__ import annotations

from core.meshing.quality_sketch_mesher import generate_quality_sketch_tri_mesh
from services.mesh_quality_service import validate_mesh_covers_geometry
from services.sketch_geometry_service import create_geometry_from_polygon_points


def _rectangle_geometry():
    return create_geometry_from_polygon_points(
        [(0.0, 0.0), (2.0, 0.0), (2.0, 1.0), (0.0, 1.0)]
    )


def _pentagon_geometry():
    return create_geometry_from_polygon_points(
        [(0.0, 0.0), (2.0, 0.0), (2.4, 0.8), (1.1, 1.6), (-0.2, 0.9)]
    )


def _trapezoid_geometry():
    return create_geometry_from_polygon_points(
        [(0.0, 0.0), (2.4, 0.0), (1.8, 1.0), (0.4, 1.0)]
    )


def _concave_geometry():
    return create_geometry_from_polygon_points(
        [(0.0, 0.0), (2.0, 0.0), (2.0, 0.6), (1.1, 0.6), (1.1, 1.3), (0.0, 1.3)]
    )


def test_rectangle_mesh_coverage_ratio_is_close_to_one():
    geometry = _rectangle_geometry()
    mesh = generate_quality_sketch_tri_mesh(geometry, target_size=0.25, min_angle=25.0)
    coverage = validate_mesh_covers_geometry(geometry, mesh, tolerance=0.08)

    assert coverage.is_valid is True
    assert coverage.relative_area_error < 0.08
    assert coverage.unused_node_ids == []
    assert coverage.missing_edge_mapping_ids == []
    assert coverage.degenerate_element_count == 0


def test_pentagon_mesh_coverage_ratio_is_close_to_one():
    geometry = _pentagon_geometry()
    mesh = generate_quality_sketch_tri_mesh(geometry, target_size=0.25, min_angle=25.0)
    coverage = validate_mesh_covers_geometry(geometry, mesh, tolerance=0.08)

    assert coverage.is_valid is True
    assert coverage.relative_area_error < 0.08
    assert len(mesh.elements) > 2
    assert coverage.unused_node_ids == []


def test_trapezoid_mesh_coverage_ratio_is_close_to_one():
    geometry = _trapezoid_geometry()
    mesh = generate_quality_sketch_tri_mesh(geometry, target_size=0.25, min_angle=25.0)
    coverage = validate_mesh_covers_geometry(geometry, mesh, tolerance=0.03)

    assert coverage.is_valid is True
    assert coverage.relative_area_error < 0.03
    assert coverage.unused_node_ids == []


def test_concave_mesh_coverage_ratio_is_close_to_one():
    geometry = _concave_geometry()
    mesh = generate_quality_sketch_tri_mesh(geometry, target_size=0.2, min_angle=25.0)
    coverage = validate_mesh_covers_geometry(geometry, mesh, tolerance=0.03)

    assert coverage.is_valid is True
    assert coverage.relative_area_error < 0.03
    assert coverage.unused_node_ids == []


def test_target_size_025_generates_more_than_two_elements_and_complete_edge_mappings():
    geometry = _rectangle_geometry()
    mesh = generate_quality_sketch_tri_mesh(geometry, target_size=0.25, min_angle=25.0)
    coverage = validate_mesh_covers_geometry(geometry, mesh, tolerance=0.08)

    assert len(mesh.elements) > 2
    assert coverage.unused_node_ids == []
    assert coverage.missing_edge_mapping_ids == []
    assert all(mesh.geometry_edge_to_mesh_element_edges[edge.id] for edge in geometry.edges)


def test_reversed_polygon_order_is_still_valid():
    geometry = create_geometry_from_polygon_points(
        [(0.0, 0.0), (0.0, 1.0), (2.0, 1.0), (2.0, 0.0)]
    )
    mesh = generate_quality_sketch_tri_mesh(geometry, target_size=0.25, min_angle=25.0)
    coverage = validate_mesh_covers_geometry(geometry, mesh, tolerance=0.08)

    assert coverage.is_valid is True
    assert coverage.relative_area_error < 0.08

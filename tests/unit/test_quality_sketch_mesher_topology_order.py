from __future__ import annotations

from core.engineering.geometry import GeometryModel
from core.meshing.quality_sketch_mesher import (
    _reconstruct_boundary_loop_from_edges,
    generate_quality_sketch_tri_mesh,
)
from services.mesh_quality_service import validate_mesh_covers_geometry
from services.sketch_geometry_service import create_geometry_from_polygon_points


def _shuffled_quad_geometry() -> GeometryModel:
    geometry = create_geometry_from_polygon_points(
        [(0.0, 0.0), (2.0, 0.0), (2.0, 1.0), (0.0, 1.0)]
    )
    geometry.points = [geometry.points[2], geometry.points[0], geometry.points[3], geometry.points[1]]
    geometry.edges = [geometry.edges[2], geometry.edges[0], geometry.edges[3], geometry.edges[1]]
    geometry.faces[0].edge_ids = ["e3", "e1", "e4", "e2"]
    return geometry


def test_reconstruct_boundary_loop_is_independent_of_point_and_edge_order():
    geometry = _shuffled_quad_geometry()
    loop = _reconstruct_boundary_loop_from_edges(geometry)

    assert len(loop.ordered_point_ids) == 4
    assert len(loop.ordered_edge_ids) == 4
    assert set(loop.ordered_point_ids) == {"p1", "p2", "p3", "p4"}
    assert set(loop.ordered_edge_ids) == {"e1", "e2", "e3", "e4"}


def test_mesh_generation_is_independent_of_storage_order():
    geometry = _shuffled_quad_geometry()
    mesh = generate_quality_sketch_tri_mesh(geometry, target_size=0.25, min_angle=25.0)
    coverage = validate_mesh_covers_geometry(geometry, mesh, tolerance=0.03)

    assert coverage.is_valid is True
    assert coverage.relative_area_error < 0.03
    assert coverage.missing_edge_mapping_ids == []

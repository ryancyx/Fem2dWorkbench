from __future__ import annotations

from core.meshing.quality_sketch_mesher import generate_quality_sketch_tri_mesh
from services.mesh_quality_service import validate_mesh_covers_geometry
from services.sketch_geometry_service import create_geometry_from_polygon_points


def test_quality_mesher_produces_complete_mesh_without_solver_dependency():
    geometry = create_geometry_from_polygon_points(
        [(0.0, 0.0), (2.0, 0.0), (2.2, 0.7), (1.0, 1.5), (-0.1, 0.8)]
    )

    mesh = generate_quality_sketch_tri_mesh(geometry, target_size=0.25, min_angle=25.0)
    coverage = validate_mesh_covers_geometry(geometry, mesh, tolerance=0.03)

    assert mesh.metadata["mesh_type"] == "gmsh_cst"
    assert mesh.metadata["mesher_backend"] == "gmsh"
    assert coverage.is_valid is True
    assert coverage.relative_area_error < 0.03
    assert coverage.unused_node_ids == []
    assert coverage.missing_edge_mapping_ids == []
    assert coverage.degenerate_element_count == 0

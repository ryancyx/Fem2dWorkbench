from __future__ import annotations

from core.meshing.quality_sketch_mesher import generate_quality_sketch_tri_mesh
from services.sketch_geometry_service import create_geometry_from_polygon_points


def test_quality_mesher_generates_gmsh_cst_mesh_with_complete_edge_mappings():
    geometry = create_geometry_from_polygon_points(
        [(0.0, 0.0), (2.0, 0.0), (2.0, 1.0), (0.0, 1.0)]
    )

    mesh = generate_quality_sketch_tri_mesh(geometry, target_size=0.25, min_angle=25.0)

    assert mesh.metadata["mesher_backend"] == "gmsh"
    assert mesh.metadata["mesh_type"] == "gmsh_cst"
    assert all(element.element_type == "CST" for element in mesh.elements)
    assert set(mesh.geometry_edge_to_mesh_element_edges) == {"e1", "e2", "e3", "e4"}
    assert all(mesh.geometry_edge_to_mesh_element_edges[edge_id] for edge_id in ("e1", "e2", "e3", "e4"))

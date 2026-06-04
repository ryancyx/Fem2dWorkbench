from __future__ import annotations

import pytest

import core.meshing.gmsh_cst_mesher as gmsh_mesher
from core.meshing.quality_sketch_mesher import generate_quality_sketch_tri_mesh
from services.sketch_geometry_service import create_geometry_from_polygon_points


def test_mesher_fails_clearly_when_gmsh_backend_is_missing(monkeypatch):
    monkeypatch.setattr(gmsh_mesher, "gmsh", None)
    geometry = create_geometry_from_polygon_points(
        [(0.0, 0.0), (2.0, 0.0), (2.0, 1.0), (0.0, 1.0)]
    )

    with pytest.raises(ValueError, match="Gmsh meshing backend is not installed"):
        generate_quality_sketch_tri_mesh(geometry, target_size=0.25, min_angle=25.0)

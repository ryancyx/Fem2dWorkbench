from __future__ import annotations

from services.mesh_quality_service import validate_mesh_covers_geometry
from ui.backend.workbench_bridge import WorkbenchBridge


def test_stage15_mesh_generation_and_solve_regression():
    bridge = WorkbenchBridge()

    assert bridge.newProject()
    assert bridge.createEmptySketchForActivePart()
    for point in ((0.0, 0.0), (2.0, 1.0), (0.0, 1.0), (2.0, 0.0)):
        assert bridge.addSketchPointFromViewport(*point)

    assert bridge.selectSketchPoint("p1")
    assert bridge.startEdgeFromSelectedPoint()
    assert bridge.connectEdgeToPoint("p4")
    assert bridge.selectSketchPoint("p4")
    assert bridge.startEdgeFromSelectedPoint()
    assert bridge.connectEdgeToPoint("p2")
    assert bridge.selectSketchPoint("p2")
    assert bridge.startEdgeFromSelectedPoint()
    assert bridge.connectEdgeToPoint("p3")
    assert bridge.selectSketchPoint("p3")
    assert bridge.startEdgeFromSelectedPoint()
    assert bridge.connectEdgeToPoint("p1")
    assert bridge.buildSketchFace()

    assert bridge.generateQualityMeshForActivePart(0.25, 0.0, 25.0)
    part = bridge.current_project.get_part_by_id(bridge.activePartId)
    coverage = validate_mesh_covers_geometry(part.geometry, bridge.current_sketch_mesh, tolerance=0.08)
    assert coverage.is_valid is True

    assert bridge.selectGeometryEdge("e4")
    assert bridge.addFixedConstraintToSelectedTarget(True, True)
    assert bridge.selectGeometryEdge("e2")
    assert bridge.addLoadToSelectedTarget("edge_uniform", 0.0, -1000.0)

    assert bridge.solveCurrentModel()
    assert bridge.hasSolution is True
    assert bridge.nodeCount > 4
    assert bridge.elementCount > 2
    assert "奇异" not in bridge.statusText

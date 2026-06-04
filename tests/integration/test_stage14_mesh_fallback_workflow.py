from __future__ import annotations

from ui.backend.workbench_bridge import WorkbenchBridge


def test_stage14_mesh_fallback_workflow():
    bridge = WorkbenchBridge()
    assert bridge.newProject() is True
    assert bridge.createEmptySketchForActivePart() is True

    for point in ((0.0, 0.0), (2.0, 0.0), (2.0, 1.0), (0.0, 1.0)):
        assert bridge.addSketchPointFromViewport(*point) is True

    assert bridge.addSketchEdge("p1", "p2") is True
    assert bridge.addSketchEdge("p2", "p3") is True
    assert bridge.addSketchEdge("p3", "p4") is True
    assert bridge.addSketchEdge("p4", "p1") is True
    assert bridge.buildSketchFace() is True

    assert bridge.generateQualityMeshForActivePart(0.25, 0.0, 25.0) is True
    assert bridge.currentMeshType == "gmsh_cst"
    assert bridge.sketchMeshNodeCount > 4
    assert bridge.sketchMeshElementCount > 2

from __future__ import annotations

from ui.backend.workbench_bridge import WorkbenchBridge


def _build_quad_sketch(bridge: WorkbenchBridge) -> None:
    assert bridge.createEmptySketchForActivePart()
    assert bridge.addSketchPoint(0.0, 0.0)
    assert bridge.addSketchPoint(2.0, 0.0)
    assert bridge.addSketchPoint(2.0, 1.0)
    assert bridge.addSketchPoint(0.0, 1.0)
    assert bridge.addSketchEdge("p1", "p2")
    assert bridge.addSketchEdge("p2", "p3")
    assert bridge.addSketchEdge("p3", "p4")
    assert bridge.addSketchEdge("p4", "p1")
    assert bridge.buildSketchFace()


def test_stage15_result_query_workflow_for_sketch_model():
    bridge = WorkbenchBridge()

    assert bridge.newProject()
    _build_quad_sketch(bridge)
    assert bridge.generateQualityMeshForActivePart(0.25, 0.0, 25.0)
    assert bridge.selectGeometryEdge("e4")
    assert bridge.addFixedConstraintToSelectedTarget(True, True)
    assert bridge.selectGeometryEdge("e2")
    assert bridge.addLoadToSelectedTarget("edge_uniform", 0.0, -1000.0)
    assert bridge.solveCurrentModel()
    assert bridge.queryResultAtPoint(1.0, 0.5)

    assert bridge.hasSolution is True
    assert bridge.resultQueryText != ""
    assert "查询点" in bridge.resultQueryText
    assert bridge.nodeRowsJson != "[]"
    assert bridge.elementRowsJson != "[]"

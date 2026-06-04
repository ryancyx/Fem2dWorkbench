from __future__ import annotations

from ui.backend.workbench_bridge import WorkbenchBridge


def _build_quad_sketch(bridge: WorkbenchBridge) -> None:
    assert bridge.createEmptySketchForActivePart()
    for point in ((0.0, 0.0), (2.0, 0.0), (2.0, 1.0), (0.0, 1.0)):
        assert bridge.addSketchPoint(*point)
    for edge in (("p1", "p2"), ("p2", "p3"), ("p3", "p4"), ("p4", "p1")):
        assert bridge.addSketchEdge(*edge)
    assert bridge.buildSketchFace()


def test_bridge_unified_solve_rectangular_model():
    bridge = WorkbenchBridge()

    assert bridge.newProject()
    assert bridge.updateCurrentProjectParameters(2.0, 1.0, 210e9, 0.3, 0.01, -1000.0, 4, 2)
    assert bridge.solveCurrentModel()
    assert bridge.hasSolution is True
    assert bridge.nodeCount == 15
    assert bridge.elementCount == 16


def test_bridge_unified_solve_sketch_model():
    bridge = WorkbenchBridge()

    assert bridge.newProject()
    _build_quad_sketch(bridge)
    assert bridge.selectGeometryEdge("e4")
    assert bridge.addFixedConstraintToSelectedTarget(True, True)
    assert bridge.selectGeometryEdge("e2")
    assert bridge.addLoadToSelectedTarget("edge_uniform", 0.0, -1000.0)
    assert bridge.solveCurrentModel()
    assert bridge.hasSolution is True
    assert bridge.nodeCount > 4
    assert bridge.elementCount > 2
    assert bridge.currentMeshType == "gmsh_cst"


def test_bridge_unified_solve_sketch_rejects_missing_constraints_or_loads():
    bridge = WorkbenchBridge()

    assert bridge.newProject()
    _build_quad_sketch(bridge)
    assert bridge.solveCurrentModel() is False
    assert "缺少约束" in bridge.statusText

    assert bridge.selectGeometryEdge("e4")
    assert bridge.addFixedConstraintToSelectedTarget(True, True)
    assert bridge.solveCurrentModel() is False
    assert "缺少载荷" in bridge.statusText


def test_bridge_unified_solve_uses_existing_quality_mesh():
    bridge = WorkbenchBridge()

    assert bridge.newProject()
    _build_quad_sketch(bridge)
    assert bridge.generateQualityMeshForActivePart(0.25, 0.0, 25.0)
    existing_node_count = bridge.sketchMeshNodeCount
    existing_element_count = bridge.sketchMeshElementCount
    assert bridge.selectGeometryPoint("p1")
    assert bridge.addFixedConstraintToSelectedTarget(True, True)
    assert bridge.selectGeometryPoint("p3")
    assert bridge.addLoadToSelectedTarget("nodal_concentrated", 0.0, -1000.0)
    assert bridge.solveCurrentModel()
    assert bridge.sketchMeshNodeCount == existing_node_count
    assert bridge.sketchMeshElementCount == existing_element_count

from __future__ import annotations

from ui.backend.workbench_bridge import WorkbenchBridge


def _build_quad_sketch(bridge: WorkbenchBridge) -> None:
    assert bridge.createEmptySketchForActivePart()
    for point in ((0.0, 0.0), (2.0, 0.0), (2.0, 1.0), (0.0, 1.0)):
        assert bridge.addSketchPoint(*point)
    for edge in (("p1", "p2"), ("p2", "p3"), ("p3", "p4"), ("p4", "p1")):
        assert bridge.addSketchEdge(*edge)
    assert bridge.buildSketchFace()


def test_bridge_add_point_and_edge_constraints_and_loads():
    bridge = WorkbenchBridge()

    assert bridge.newProject()
    _build_quad_sketch(bridge)

    assert bridge.selectGeometryPoint("p1")
    assert bridge.addFixedConstraintToSelectedTarget(True, True)
    assert "geometry_point:p1" in bridge.boundaryConditionRowsPreview

    assert bridge.selectGeometryEdge("e4")
    assert bridge.addFixedConstraintToSelectedTarget(True, False)
    assert "geometry_edge:e4" in bridge.boundaryConditionRowsPreview

    assert bridge.selectGeometryPoint("p3")
    assert bridge.addLoadToSelectedTarget("nodal_concentrated", 10.0, -20.0)
    assert "nodal_concentrated" in bridge.loadRowsPreview
    assert "geometry_point:p3" in bridge.loadRowsPreview

    assert bridge.selectGeometryEdge("e2")
    assert bridge.addLoadToSelectedTarget("edge_uniform", 0.0, -1000.0)
    assert "geometry_edge:e2" in bridge.loadRowsPreview


def test_bridge_delete_and_clear_constraints_and_loads():
    bridge = WorkbenchBridge()

    assert bridge.newProject()
    _build_quad_sketch(bridge)
    assert bridge.selectGeometryEdge("e4")
    assert bridge.addFixedConstraintToSelectedTarget(True, True)
    bc_id = bridge.boundaryConditionRowsPreview.split(" | ")[0]
    assert bridge.deleteBoundaryCondition(bc_id)
    assert bridge.boundaryConditionRowsPreview == ""

    assert bridge.selectGeometryEdge("e2")
    assert bridge.addLoadToSelectedTarget("edge_uniform", 0.0, -1000.0)
    load_id = bridge.loadRowsPreview.split(" | ")[0]
    assert bridge.deleteLoad(load_id)
    assert bridge.loadRowsPreview == ""

    assert bridge.selectGeometryPoint("p1")
    assert bridge.addFixedConstraintToSelectedTarget(True, True)
    assert bridge.clearConstraints()
    assert bridge.boundaryConditionRowsPreview == ""

    assert bridge.selectGeometryPoint("p3")
    assert bridge.addLoadToSelectedTarget("nodal_concentrated", 0.0, -500.0)
    assert bridge.clearLoads()
    assert bridge.loadRowsPreview == ""

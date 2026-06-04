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


def test_bridge_select_sketch_edge():
    bridge = WorkbenchBridge()

    assert bridge.newProject()
    _build_quad_sketch(bridge)

    assert bridge.selectSketchEdge("e2") is True
    assert bridge.selectedSketchEdgeId == "e2"


def test_bridge_select_missing_sketch_edge_fails():
    bridge = WorkbenchBridge()

    assert bridge.newProject()
    _build_quad_sketch(bridge)

    assert bridge.selectSketchEdge("bad") is False
    assert "失败" in bridge.statusText


def test_bridge_set_selected_edge_as_fixed_and_load():
    bridge = WorkbenchBridge()

    assert bridge.newProject()
    _build_quad_sketch(bridge)

    assert bridge.selectSketchEdge("e4")
    assert bridge.setSelectedSketchEdgeAsFixed()
    assert bridge.sketchFixedEdgeId == "e4"

    assert bridge.selectSketchEdge("e2")
    assert bridge.setSelectedSketchEdgeAsLoad()
    assert bridge.sketchLoadEdgeId == "e2"


def test_bridge_clear_sketch_boundary_load_selection():
    bridge = WorkbenchBridge()

    assert bridge.newProject()
    _build_quad_sketch(bridge)
    assert bridge.selectSketchEdge("e4")
    assert bridge.setSelectedSketchEdgeAsFixed()
    assert bridge.selectSketchEdge("e2")
    assert bridge.setSelectedSketchEdgeAsLoad()

    assert bridge.clearSketchBoundaryLoadSelection()
    assert bridge.selectedSketchEdgeId == ""
    assert bridge.sketchFixedEdgeId == ""
    assert bridge.sketchLoadEdgeId == ""


def test_bridge_delete_edge_clears_invalid_selection():
    bridge = WorkbenchBridge()

    assert bridge.newProject()
    _build_quad_sketch(bridge)
    assert bridge.selectSketchEdge("e2")
    assert bridge.setSelectedSketchEdgeAsLoad()

    assert bridge.deleteSketchEdge("e2")
    assert bridge.selectedSketchEdgeId == ""
    assert bridge.sketchLoadEdgeId == ""


def test_bridge_solve_sketch_uses_stored_edge_selection():
    bridge = WorkbenchBridge()

    assert bridge.newProject()
    _build_quad_sketch(bridge)
    assert bridge.generateSketchMeshForActivePart()
    assert bridge.selectSketchEdge("e4")
    assert bridge.setSelectedSketchEdgeAsFixed()
    assert bridge.selectSketchEdge("e2")
    assert bridge.setSelectedSketchEdgeAsLoad()
    assert bridge.setSketchLoadValues(0.0, -1000.0)

    assert bridge.solveSketchProject("", "", bridge.sketchLoadQx, bridge.sketchLoadQy)
    assert bridge.hasSolution is True
    assert bridge.currentMeshType == "gmsh_cst"
    assert bridge.nodeCount > 4
    assert bridge.elementCount > 2

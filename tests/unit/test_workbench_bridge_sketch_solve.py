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


def _build_triangle_sketch(bridge: WorkbenchBridge) -> None:
    assert bridge.createEmptySketchForActivePart()
    assert bridge.addSketchPoint(0.0, 0.0)
    assert bridge.addSketchPoint(2.0, 0.0)
    assert bridge.addSketchPoint(1.0, 1.0)
    assert bridge.addSketchEdge("p1", "p2")
    assert bridge.addSketchEdge("p2", "p3")
    assert bridge.addSketchEdge("p3", "p1")
    assert bridge.buildSketchFace()


def test_bridge_solve_quad_sketch_with_edge_bc_and_load():
    bridge = WorkbenchBridge()

    assert bridge.newProject()
    _build_quad_sketch(bridge)
    assert bridge.generateSketchMeshForActivePart()

    ok = bridge.solveSketchProject("e4", "e2", 0.0, -1000.0)

    assert ok is True
    assert bridge.hasSolution is True
    assert bridge.currentMeshType == "gmsh_cst"
    assert bridge.nodeCount > 4
    assert bridge.elementCount > 2
    assert bridge.nodeRowsPreview != ""
    assert bridge.elementRowsPreview != ""
    assert "草图求解完成" in bridge.statusText


def test_bridge_solve_triangle_sketch_with_edge_bc_and_load():
    bridge = WorkbenchBridge()

    assert bridge.newProject()
    _build_triangle_sketch(bridge)

    ok = bridge.solveSketchProject("e3", "e2", 0.0, -500.0)

    assert ok is True
    assert bridge.hasSolution is True
    assert bridge.currentMeshType == "gmsh_cst"
    assert bridge.nodeCount > 3
    assert bridge.elementCount > 1


def test_bridge_solve_sketch_auto_generates_mesh_when_missing():
    bridge = WorkbenchBridge()

    assert bridge.newProject()
    _build_quad_sketch(bridge)
    assert bridge.hasSketchMesh is False

    ok = bridge.solveSketchProject("e4", "e2", 0.0, -1000.0)

    assert ok is True
    assert bridge.hasSketchMesh is True
    assert bridge.currentMeshType == "gmsh_cst"
    assert bridge.sketchMeshNodeCount > 4
    assert bridge.sketchMeshElementCount > 2


def test_bridge_solve_sketch_rejects_missing_fixed_edge():
    bridge = WorkbenchBridge()

    assert bridge.newProject()
    _build_quad_sketch(bridge)

    ok = bridge.solveSketchProject("missing", "e2", 0.0, -1000.0)

    assert ok is False
    assert "固定边不存在" in bridge.statusText


def test_bridge_solve_sketch_rejects_missing_load_edge():
    bridge = WorkbenchBridge()

    assert bridge.newProject()
    _build_quad_sketch(bridge)

    ok = bridge.solveSketchProject("e4", "missing", 0.0, -1000.0)

    assert ok is False
    assert "载荷边不存在" in bridge.statusText


def test_bridge_solve_sketch_rejects_unclosed_sketch():
    bridge = WorkbenchBridge()

    assert bridge.newProject()
    assert bridge.createEmptySketchForActivePart()
    assert bridge.addSketchPoint(0.0, 0.0)
    assert bridge.addSketchPoint(1.0, 0.0)
    assert bridge.addSketchPoint(0.0, 1.0)
    assert bridge.addSketchEdge("p1", "p2")
    assert bridge.addSketchEdge("p2", "p3")

    ok = bridge.solveSketchProject("e1", "e2", 0.0, -1000.0)

    assert ok is False
    assert "草图求解失败" in bridge.statusText


def test_bridge_solve_sketch_rejects_zero_load():
    bridge = WorkbenchBridge()

    assert bridge.newProject()
    _build_quad_sketch(bridge)

    ok = bridge.solveSketchProject("e4", "e2", 0.0, 0.0)

    assert ok is False
    assert "不能同时为 0" in bridge.statusText

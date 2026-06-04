from __future__ import annotations

from core.engineering.mesh_model import MeshNode
from ui.backend.workbench_bridge import WorkbenchBridge


def _build_quad_sketch(bridge: WorkbenchBridge) -> None:
    assert bridge.createEmptySketchForActivePart()
    for point in ((0.0, 0.0), (2.0, 0.0), (2.0, 1.0), (0.0, 1.0)):
        assert bridge.addSketchPoint(*point)
    for edge in (("p1", "p2"), ("p2", "p3"), ("p3", "p4"), ("p4", "p1")):
        assert bridge.addSketchEdge(*edge)
    assert bridge.buildSketchFace()


def test_solve_current_model_rejects_missing_closed_face():
    bridge = WorkbenchBridge()

    assert bridge.newProject()
    assert bridge.createEmptySketchForActivePart()
    assert bridge.solveCurrentModel() is False
    assert "闭合面" in bridge.statusText


def test_solve_current_model_rejects_invalid_mesh_before_solver(monkeypatch):
    bridge = WorkbenchBridge()

    assert bridge.newProject()
    _build_quad_sketch(bridge)
    assert bridge.generateQualityMeshForActivePart(0.25, 0.0, 25.0)
    bridge.current_sketch_mesh.nodes.append(MeshNode(id=999, x=9.0, y=9.0))
    bridge.current_mesh_type = "gmsh_cst"
    assert bridge.selectGeometryEdge("e4")
    assert bridge.addFixedConstraintToSelectedTarget(True, True)
    assert bridge.selectGeometryEdge("e2")
    assert bridge.addLoadToSelectedTarget("edge_uniform", 0.0, -1000.0)

    def _should_not_run(_model):
        raise AssertionError("solver should not be called for invalid mesh")

    monkeypatch.setattr("ui.backend.workbench_bridge.solve_static_linear", _should_not_run)
    assert bridge.solveCurrentModel() is False
    assert "未连接网格节点" in bridge.statusText


def test_solve_current_model_rejects_missing_constraints_or_loads():
    bridge = WorkbenchBridge()

    assert bridge.newProject()
    _build_quad_sketch(bridge)
    assert bridge.generateQualityMeshForActivePart(0.25, 0.0, 25.0)
    assert bridge.solveCurrentModel() is False
    assert "缺少约束" in bridge.statusText

    assert bridge.selectGeometryEdge("e4")
    assert bridge.addFixedConstraintToSelectedTarget(True, True)
    assert bridge.solveCurrentModel() is False
    assert "缺少载荷" in bridge.statusText


def test_solve_current_model_accepts_valid_mesh_and_runs():
    bridge = WorkbenchBridge()

    assert bridge.newProject()
    _build_quad_sketch(bridge)
    assert bridge.generateQualityMeshForActivePart(0.25, 0.0, 25.0)
    assert bridge.selectGeometryEdge("e4")
    assert bridge.addFixedConstraintToSelectedTarget(True, True)
    assert bridge.selectGeometryEdge("e2")
    assert bridge.addLoadToSelectedTarget("edge_uniform", 0.0, -1000.0)
    assert bridge.solveCurrentModel() is True
    assert bridge.hasSolution is True

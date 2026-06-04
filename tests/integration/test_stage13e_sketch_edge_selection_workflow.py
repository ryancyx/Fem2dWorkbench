from __future__ import annotations

from pathlib import Path

from ui.backend.workbench_bridge import WorkbenchBridge


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAIN_WORKBENCH_QML = PROJECT_ROOT / "ui" / "qml" / "MainWorkbench.qml"


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


def test_stage13e_sketch_edge_selection_workflow(tmp_path):
    bridge = WorkbenchBridge()

    assert bridge.newProject()
    _build_quad_sketch(bridge)
    assert bridge.generateSketchMeshForActivePart()
    assert bridge.selectSketchEdge("e4")
    assert bridge.setSelectedSketchEdgeAsFixed()
    assert bridge.selectSketchEdge("e2")
    assert bridge.setSelectedSketchEdgeAsLoad()
    assert bridge.setSketchLoadValues(0.0, -1000.0)
    assert bridge.solveSketchProject("", "", 0.0, -1000.0)

    assert bridge.hasSolution is True
    assert bridge.currentMeshType == "gmsh_cst"
    assert bridge.nodeCount > 4
    assert bridge.elementCount > 2
    assert bridge.nodeRowsPreview != ""
    assert bridge.elementRowsPreview != ""

    file_path = tmp_path / "stage13e_sketch_edges.f2dw.json"
    assert bridge.saveCurrentProject(str(file_path))

    restored = WorkbenchBridge()
    assert restored.loadProject(str(file_path))
    assert restored.sketchPointCount == 4
    assert restored.sketchEdgeCount == 4
    assert restored.sketchFaceCount == 1

    assert restored.selectSketchEdge("e4")
    assert restored.setSelectedSketchEdgeAsFixed()
    assert restored.selectSketchEdge("e2")
    assert restored.setSelectedSketchEdgeAsLoad()
    assert restored.setSketchLoadValues(0.0, -1000.0)
    assert restored.solveSketchProject("", "", 0.0, -1000.0)
    assert restored.hasSolution is True
    assert restored.currentMeshType == "gmsh_cst"
    assert restored.nodeCount > 4
    assert restored.elementCount > 2


def test_stage13e_qml_contains_sketch_edge_selection_entries():
    qml_text = MAIN_WORKBENCH_QML.read_text(encoding="utf-8")

    required_snippets = [
        "selectedSketchEdgeId",
        "sketchFixedEdgeId",
        "sketchLoadEdgeId",
        "sketchLoadQx",
        "sketchLoadQy",
        "selectSketchEdge",
        "setSelectedSketchEdgeAsFixed",
        "setSelectedSketchEdgeAsLoad",
        "setSketchLoadValues",
        "clearSketchBoundaryLoadSelection",
        "当前选中边",
        "设为固定边",
        "设为载荷边",
        "清除边界/载荷设置",
        "distancePointToSegment",
        "findNearestSketchEdgeAt",
    ]

    for snippet in required_snippets:
        assert snippet in qml_text, f"Missing stage 13E QML snippet: {snippet}"

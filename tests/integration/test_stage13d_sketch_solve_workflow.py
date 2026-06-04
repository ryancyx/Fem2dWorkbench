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


def test_stage13d_sketch_save_load_mesh_solve_export_workflow(tmp_path):
    bridge = WorkbenchBridge()

    assert bridge.newProject()
    _build_quad_sketch(bridge)
    assert bridge.generateSketchMeshForActivePart()
    assert bridge.solveSketchProject("e4", "e2", 0.0, -1000.0)

    assert bridge.hasSolution is True
    assert bridge.currentMeshType == "gmsh_cst"
    assert bridge.nodeCount > 4
    assert bridge.elementCount > 2
    assert bridge.nodeRowsPreview != ""
    assert bridge.elementRowsPreview != ""

    export_dir = tmp_path / "sketch_exports"
    assert bridge.exportResults(str(export_dir))
    assert (export_dir / "node_displacements.csv").exists()
    assert (export_dir / "element_results.csv").exists()
    assert (export_dir / "summary.txt").exists()

    file_path = tmp_path / "stage13d_sketch_solve.f2dw.json"
    assert bridge.saveCurrentProject(str(file_path))

    restored = WorkbenchBridge()
    assert restored.loadProject(str(file_path))
    assert restored.sketchPointCount == 4
    assert restored.sketchEdgeCount == 4
    assert restored.sketchFaceCount == 1
    assert restored.hasSketchMesh is False

    assert restored.generateSketchMeshForActivePart()
    assert restored.solveSketchProject("e4", "e2", 0.0, -1000.0)
    assert restored.currentMeshType == "gmsh_cst"
    assert restored.nodeCount > 4
    assert restored.elementCount > 2


def test_stage13d_rectangular_legacy_solve_still_works():
    bridge = WorkbenchBridge()

    assert bridge.newProject()
    assert bridge.updateCurrentProjectParameters(2.0, 1.0, 210e9, 0.3, 0.01, -1000.0, 4, 2)
    assert bridge.solveCurrentProject(4, 2)

    assert bridge.hasSolution is True
    assert bridge.nodeCount == 15
    assert bridge.elementCount == 16


def test_stage13d_qml_contains_sketch_solve_entries():
    qml_text = MAIN_WORKBENCH_QML.read_text(encoding="utf-8")

    required_snippets = [
        "sketchFixedEdgeId",
        "sketchLoadEdgeId",
        "sketchLoadQx",
        "sketchLoadQy",
        "solveSketchProject",
        "bridge.solveSketchProject",
        "固定边 ID",
        "载荷边 ID",
        "求解草图",
        "草图求解",
    ]

    for snippet in required_snippets:
        assert snippet in qml_text, f"Missing stage 13D QML snippet: {snippet}"

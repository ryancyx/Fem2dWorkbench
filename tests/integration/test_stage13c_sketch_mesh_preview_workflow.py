from __future__ import annotations

import json
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


def test_stage13c_bridge_save_load_then_generate_sketch_mesh(tmp_path):
    bridge = WorkbenchBridge()

    assert bridge.newProject()
    _build_quad_sketch(bridge)
    assert bridge.generateSketchMeshForActivePart()

    assert bridge.hasSketchMesh is True
    assert bridge.currentMeshType == "gmsh_cst"
    assert bridge.sketchMeshNodeCount > 4
    assert bridge.sketchMeshElementCount > 2

    file_path = tmp_path / "stage13c_sketch_mesh_project.f2dw.json"
    assert bridge.saveCurrentProject(str(file_path))

    restored = WorkbenchBridge()
    assert restored.loadProject(str(file_path))

    assert restored.sketchPointCount == 4
    assert restored.sketchEdgeCount == 4
    assert restored.sketchFaceCount == 1
    assert restored.hasSketchMesh is False

    assert restored.generateSketchMeshForActivePart()
    assert restored.hasSketchMesh is True
    assert restored.currentMeshType == "gmsh_cst"
    assert restored.sketchMeshNodeCount > 4
    assert restored.sketchMeshElementCount > 2

    nodes = json.loads(restored.sketchMeshNodesJson)
    elements = json.loads(restored.sketchMeshElementsJson)

    assert len(nodes) == restored.sketchMeshNodeCount
    assert len(elements) == restored.sketchMeshElementCount
    assert all(len(element["node_ids"]) == 3 for element in elements)


def test_stage13c_clear_sketch_mesh_keeps_sketch_geometry():
    bridge = WorkbenchBridge()

    assert bridge.newProject()
    _build_quad_sketch(bridge)
    assert bridge.generateSketchMeshForActivePart()

    assert bridge.clearSketchMesh()

    assert bridge.hasSketchMesh is False
    assert bridge.sketchMeshNodeCount == 0
    assert bridge.sketchMeshElementCount == 0
    assert bridge.sketchPointCount == 4
    assert bridge.sketchEdgeCount == 4
    assert bridge.sketchFaceCount == 1
    assert bridge.sketchHasFace is True


def test_stage13c_qml_contains_sketch_mesh_preview_entries():
    qml_text = MAIN_WORKBENCH_QML.read_text(encoding="utf-8")

    required_snippets = [
        "sketchMeshNodes",
        "sketchMeshElements",
        "bridge.sketchMeshNodesJson",
        "bridge.sketchMeshElementsJson",
        "onSketchMeshChanged",
        "bridge.hasSketchMesh",
        "bridge.sketchMeshNodeCount",
        "bridge.sketchMeshElementCount",
        "bridge.sketchMeshStatusText",
        "bridge.generateSketchMeshForActivePart",
        "bridge.clearSketchMesh",
        "生成草图网格",
        "清除草图网格",
        "网格节点数",
        "网格单元数",
    ]

    for snippet in required_snippets:
        assert snippet in qml_text, f"Missing stage 13C QML snippet: {snippet}"

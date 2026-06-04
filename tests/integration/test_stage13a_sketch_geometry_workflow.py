from __future__ import annotations

from ui.backend.workbench_bridge import WorkbenchBridge


def test_stage13a_sketch_geometry_workflow(tmp_path):
    bridge = WorkbenchBridge()
    assert bridge.newProject()
    assert bridge.createEmptySketchForActivePart()
    assert bridge.addSketchPoint(0.0, 0.0)
    assert bridge.addSketchPoint(2.0, 0.0)
    assert bridge.addSketchPoint(1.0, 1.0)
    assert bridge.addSketchEdge("p1", "p2")
    assert bridge.addSketchEdge("p2", "p3")
    assert bridge.addSketchEdge("p3", "p1")
    assert bridge.sketchCanBuildFace is True
    assert bridge.buildSketchFace()
    assert bridge.sketchHasFace is True

    file_path = tmp_path / "sketch_project.f2dw.json"
    assert bridge.saveCurrentProject(str(file_path))

    restored = WorkbenchBridge()
    assert restored.loadProject(str(file_path))
    assert restored.sketchPointCount == 3
    assert restored.sketchEdgeCount == 3
    assert restored.sketchFaceCount == 1
    assert '"id": "p1"' in restored.sketchPointsJson
    assert '"id": "p2"' in restored.sketchPointsJson
    assert '"id": "p3"' in restored.sketchPointsJson

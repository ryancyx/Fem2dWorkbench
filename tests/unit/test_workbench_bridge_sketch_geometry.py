from __future__ import annotations

from ui.backend.workbench_bridge import WorkbenchBridge


def test_bridge_create_empty_sketch_for_active_part():
    bridge = WorkbenchBridge()
    assert bridge.newProject()

    assert bridge.createEmptySketchForActivePart()

    assert bridge.sketchPointCount == 0
    assert bridge.sketchEdgeCount == 0
    assert bridge.sketchFaceCount == 0


def test_bridge_add_points_and_edges_build_triangle_face():
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
    assert bridge.sketchFaceCount == 1
    assert bridge.sketchHasFace is True


def test_bridge_sketch_json_contains_points_and_edges():
    bridge = WorkbenchBridge()
    assert bridge.newProject()
    assert bridge.createEmptySketchForActivePart()

    assert bridge.addSketchPoint(0.0, 0.0)
    assert bridge.addSketchPoint(1.0, 0.0)
    assert bridge.addSketchEdge("p1", "p2")

    assert '"id": "p1"' in bridge.sketchPointsJson
    assert '"id": "p2"' in bridge.sketchPointsJson
    assert '"id": "e1"' in bridge.sketchEdgesJson


def test_bridge_clear_sketch():
    bridge = WorkbenchBridge()
    assert bridge.newProject()
    assert bridge.createEmptySketchForActivePart()
    assert bridge.addSketchPoint(0.0, 0.0)

    assert bridge.clearSketch()

    assert bridge.sketchPointCount == 0
    assert bridge.sketchEdgeCount == 0
    assert bridge.sketchFaceCount == 0


def test_bridge_rejects_invalid_edge():
    bridge = WorkbenchBridge()
    assert bridge.newProject()
    assert bridge.createEmptySketchForActivePart()
    assert bridge.addSketchPoint(0.0, 0.0)

    assert bridge.addSketchEdge("p1", "missing") is False
    assert "失败" in bridge.statusText

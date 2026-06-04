from __future__ import annotations

from ui.backend.workbench_bridge import WorkbenchBridge


def test_bridge_create_empty_sketch_on_empty_project_creates_part_without_instance():
    bridge = WorkbenchBridge()

    assert bridge.newProject()
    assert bridge.partCount == 0
    assert bridge.instanceCount == 0

    assert bridge.createEmptySketchForActivePart()
    assert bridge.partCount == 1
    assert bridge.instanceCount == 0
    assert bridge.activePartId != ""
    assert bridge.activeInstanceId == ""
    assert bridge.sketchPointCount == 0
    assert bridge.sketchEdgeCount == 0


def test_bridge_add_sketch_point_from_viewport_on_empty_project_bootstraps_sketch_part():
    bridge = WorkbenchBridge()

    assert bridge.newProject()
    assert bridge.addSketchPointFromViewport(0.0, 0.0)
    assert bridge.partCount == 1
    assert bridge.instanceCount == 0
    assert bridge.sketchPointCount == 1
    assert "p1" in bridge.sketchPointsPreview

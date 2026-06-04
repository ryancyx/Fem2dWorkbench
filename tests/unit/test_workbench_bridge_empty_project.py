from __future__ import annotations

from ui.backend.workbench_bridge import WorkbenchBridge


def test_bridge_new_project_creates_empty_project_state():
    bridge = WorkbenchBridge()

    assert bridge.newProject()
    assert bridge.hasProject is True
    assert bridge.projectName == "untitled_project"
    assert bridge.partCount == 0
    assert bridge.instanceCount == 0
    assert bridge.activePartId == ""
    assert bridge.activeInstanceId == ""
    assert bridge.sketchPointCount == 0
    assert bridge.sketchEdgeCount == 0


def test_bridge_empty_project_can_still_create_default_rectangle_by_update():
    bridge = WorkbenchBridge()

    assert bridge.newProject()
    assert bridge.updateCurrentProjectParameters(2.0, 1.0, 210e9, 0.3, 0.01, -1000.0, 4, 2)
    assert bridge.partCount == 1
    assert bridge.instanceCount == 0
    assert bridge.activePartId != ""
    assert bridge.activeInstanceId == ""

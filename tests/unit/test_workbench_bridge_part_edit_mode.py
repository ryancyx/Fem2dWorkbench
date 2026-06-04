from __future__ import annotations

from ui.backend.workbench_bridge import WorkbenchBridge


def test_bridge_part_edit_mode_add_select_connect_and_exit():
    bridge = WorkbenchBridge()

    assert bridge.newProject()
    assert bridge.createEmptySketchForActivePart()
    assert bridge.enterPartEditMode()
    assert bridge.partEditMode is True

    assert bridge.setPartEditTool("添加节点")
    assert bridge.addSketchPointFromViewport(0.0, 0.0)
    assert bridge.addSketchPointFromViewport(2.0, 0.0)
    assert bridge.sketchPointCount == 2

    assert bridge.selectSketchPoint("p1")
    assert bridge.selectedSketchPointId == "p1"
    assert bridge.startEdgeFromSelectedPoint()
    assert bridge.edgeStartPointId == "p1"
    assert bridge.connectEdgeToPoint("p2")
    assert bridge.sketchEdgeCount == 1
    assert bridge.edgeStartPointId == ""

    assert "p1" in bridge.sketchNodeRowsPreview
    assert "e1" in bridge.sketchEdgeRowsPreview

    assert bridge.exitPartEditMode()
    assert bridge.partEditMode is False
    assert bridge.partEditTool == "选择"


def test_bridge_update_selected_sketch_point_and_delete_selected_entity():
    bridge = WorkbenchBridge()

    assert bridge.newProject()
    assert bridge.createEmptySketchForActivePart()
    assert bridge.addSketchPoint(0.0, 0.0)
    assert bridge.addSketchPoint(1.0, 0.0)
    assert bridge.selectSketchPoint("p1")
    assert bridge.updateSelectedSketchPoint(0.5, 0.25)
    assert "(0.500" in bridge.sketchPointsPreview

    assert bridge.selectSketchPoint("p2")
    assert bridge.deleteSelectedSketchEntity()
    assert bridge.sketchPointCount == 1

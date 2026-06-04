from __future__ import annotations

from ui.backend.workbench_bridge import WorkbenchBridge


def test_move_active_instance_reference_point_to_target_coordinate():
    bridge = WorkbenchBridge()

    assert bridge.newProject()
    assert bridge.addEmptySketchPart("part")
    assert bridge.addInstanceForPart(bridge.activePartId, "inst", 0.0, 0.0)

    assert bridge.moveActiveInstanceReferencePointTo(1.0, 0.5, 5.0, 2.0)

    assert bridge.activeInstanceTx == 4.0
    assert bridge.activeInstanceTy == 1.5
    assert "参考点" in bridge.statusText


def test_move_instance_by_delta_updates_active_instance():
    bridge = WorkbenchBridge()

    assert bridge.newProject()
    assert bridge.addEmptySketchPart("part")
    assert bridge.addInstanceForPart(bridge.activePartId, "inst", 1.0, 1.0)

    assert bridge.moveInstanceByDelta(bridge.activeInstanceId, 2.0, -0.5)

    assert bridge.activeInstanceTx == 3.0
    assert bridge.activeInstanceTy == 0.5

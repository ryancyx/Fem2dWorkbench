from __future__ import annotations

from ui.backend.workbench_bridge import WorkbenchBridge


def test_stage16_assembly_instance_workflow():
    bridge = WorkbenchBridge()
    assert bridge.newProject()
    assert bridge.addEmptySketchPart("A")
    part_a = bridge.activePartId
    assert bridge.addEmptySketchPart("B")
    part_b = bridge.activePartId

    assert bridge.instanceCount == 0
    assert bridge.addInstanceForPart(part_a, "A1", 0.0, 0.0)
    inst_a = bridge.activeInstanceId
    assert bridge.addInstanceForPart(part_b, "B1", 2.0, 1.0)
    assert bridge.instanceCount == 2

    assert bridge.setActiveInstance(inst_a)
    assert bridge.moveInstanceByDelta(inst_a, 1.0, 0.5)
    assert bridge.activeInstanceTx == 1.0
    assert bridge.activeInstanceTy == 0.5

    assert bridge.deleteActiveInstance()
    assert bridge.instanceCount == 1

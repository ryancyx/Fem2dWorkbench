from __future__ import annotations

from ui.backend.workbench_bridge import WorkbenchBridge


def test_new_project_starts_without_instances_and_can_create_delete():
    bridge = WorkbenchBridge()

    assert bridge.newProject()
    assert bridge.instanceCount == 0
    assert bridge.addEmptySketchPart("part A")
    part_id = bridge.activePartId
    assert bridge.instanceCount == 0

    assert bridge.addInstanceForPart(part_id, "A1", 1.0, 2.0)
    assert bridge.instanceCount == 1
    assert bridge.activeInstancePartId == part_id
    assert bridge.activeInstanceTx == 1.0
    assert bridge.activeInstanceTy == 2.0
    assert bridge.instanceOptions[0].startswith("inst_1 | A1 |")

    assert bridge.deleteActiveInstance()
    assert bridge.instanceCount == 0
    assert bridge.activeInstanceId == ""


def test_set_active_instance_switches_part_context():
    bridge = WorkbenchBridge()

    assert bridge.newProject()
    assert bridge.addEmptySketchPart("A")
    part_a = bridge.activePartId
    assert bridge.addEmptySketchPart("B")
    part_b = bridge.activePartId
    assert bridge.addInstanceForPart(part_a, "A1", 0.0, 0.0)
    inst_a = bridge.activeInstanceId
    assert bridge.addInstanceForPart(part_b, "B1", 2.0, 0.0)

    assert bridge.setActiveInstance(inst_a)
    assert bridge.activeInstancePartId == part_a
    assert bridge.activePartId == part_a

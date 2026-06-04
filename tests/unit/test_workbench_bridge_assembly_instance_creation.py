from __future__ import annotations

import json

from ui.backend.workbench_bridge import WorkbenchBridge


def _build_face_part(bridge: WorkbenchBridge, name: str, width: float, height: float) -> str:
    assert bridge.addEmptySketchPart(name)
    assert bridge.createEmptySketchForActivePart()
    for x, y in ((0.0, 0.0), (width, 0.0), (width, height), (0.0, height)):
        assert bridge.addSketchPoint(x, y)
    for a, b in (("p1", "p2"), ("p2", "p3"), ("p3", "p4"), ("p4", "p1")):
        assert bridge.addSketchEdge(a, b)
    assert bridge.buildSketchFace()
    return bridge.activePartId


def test_new_project_starts_without_instances_and_can_create_delete_multiple():
    bridge = WorkbenchBridge()

    assert bridge.newProject()
    assert bridge.instanceCount == 0
    part_a = _build_face_part(bridge, "part A", 1.0, 1.0)
    part_b = _build_face_part(bridge, "part B", 2.0, 0.5)

    assert bridge.addInstanceForPart(part_a, "A1", 1.0, 2.0)
    first_instance_id = bridge.activeInstanceId
    assert bridge.addInstanceForPart(part_b, "B1", -0.5, 0.25)
    second_instance_id = bridge.activeInstanceId

    assert bridge.instanceCount == 2
    assert len(bridge.instanceOptions) == 2
    assert bridge.instanceOptions[0].startswith("inst_1 | A1 |")
    assert bridge.instanceOptions[1].startswith("inst_2 | B1 |")

    payload = json.loads(bridge.assemblyInstancesJson)
    assert isinstance(payload, list)
    assert len(payload) == 2
    assert payload[0]["part_id"] == part_a
    assert payload[1]["part_id"] == part_b
    for row in payload:
        assert "points" in row
        assert "edges" in row
        assert "faces" in row
        assert "tx" in row
        assert "ty" in row
        assert "part_id" in row

    assert bridge.setActiveInstance(first_instance_id)
    assert bridge.activeInstancePartId == part_a

    assert bridge.setActiveInstance(second_instance_id)
    assert bridge.deleteActiveInstance()
    assert bridge.instanceCount == 1
    assert json.loads(bridge.assemblyInstancesJson)[0]["part_id"] == part_a


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

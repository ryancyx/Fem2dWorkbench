from __future__ import annotations

import json

from ui.backend.workbench_bridge import WorkbenchBridge


def _build_quad(bridge: WorkbenchBridge) -> None:
    assert bridge.createEmptySketchForActivePart()
    for x, y in ((0.0, 0.0), (2.0, 0.0), (2.0, 1.0), (0.0, 1.0)):
        assert bridge.addSketchPoint(x, y)
    for a, b in (("p1", "p2"), ("p2", "p3"), ("p3", "p4"), ("p4", "p1")):
        assert bridge.addSketchEdge(a, b)
    assert bridge.buildSketchFace()


def test_assign_material_to_selected_face_updates_json():
    bridge = WorkbenchBridge()
    assert bridge.newProject()
    _build_quad(bridge)
    assert bridge.addMaterial("green", 1000.0, 0.25, "#00AA00")
    material_id = next(option.split("|")[0].strip() for option in bridge.materialOptions if "green" in option)

    assert bridge.selectGeometryFace("f1")
    assert bridge.assignMaterialToSelectedFace(material_id, 0.02)

    rows = json.loads(bridge.activePartFaceMaterialJson)
    assert rows[0]["face_id"] == "f1"
    assert rows[0]["material_id"] == material_id
    assert rows[0]["material_color"] == "#00AA00"


def test_assign_material_to_selected_face_requires_face_selection():
    bridge = WorkbenchBridge()
    assert bridge.newProject()
    _build_quad(bridge)

    assert bridge.assignMaterialToSelectedFace("mat_steel", 0.01) is False
    assert "闭合面" in bridge.statusText


def test_set_active_part_syncs_face_material_state():
    bridge = WorkbenchBridge()
    assert bridge.newProject()
    _build_quad(bridge)
    first_part_id = bridge.activePartId
    assert bridge.addEmptySketchPart("second")
    second_part_id = bridge.activePartId

    assert bridge.setActivePart(first_part_id)
    assert bridge.activePartId == first_part_id
    assert bridge.sketchFaceCount == 1
    assert json.loads(bridge.activePartFaceMaterialJson)[0]["face_id"] == "f1"
    assert bridge.setActivePart(second_part_id)
    assert bridge.activePartId == second_part_id
    assert bridge.sketchFaceCount == 0
    assert bridge.activePartFaceMaterialJson == "[]"

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


def test_stage16_face_material_workflow_switches_parts_and_colors():
    bridge = WorkbenchBridge()
    assert bridge.newProject()
    part_a = _build_face_part(bridge, "A", 1.0, 1.0)
    part_b = _build_face_part(bridge, "B", 2.0, 0.5)
    assert bridge.addMaterial("red", 1000.0, 0.25, "#CC0000")
    red_id = next(option.split("|")[0].strip() for option in bridge.materialOptions if "red" in option)

    assert bridge.setActivePart(part_a)
    points_a = json.loads(bridge.sketchPointsJson)
    assert points_a[2]["x"] == 1.0
    assert bridge.activePartName == "A"
    assert bridge.selectGeometryFace("f1")
    assert bridge.assignMaterialToSelectedFace(red_id, 0.02)
    assert json.loads(bridge.activePartFaceMaterialJson)[0]["material_color"] == "#CC0000"

    assert bridge.setActivePart(part_b)
    assert bridge.activePartId == part_b
    assert bridge.activePartName == "B"
    assert bridge.selectedSketchFaceId == ""
    points_b = json.loads(bridge.sketchPointsJson)
    assert points_b[2]["x"] == 2.0
    assert json.loads(bridge.activePartFaceMaterialJson)[0]["material_id"] != red_id

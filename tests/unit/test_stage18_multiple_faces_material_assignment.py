from __future__ import annotations

import json

from ui.backend.workbench_bridge import WorkbenchBridge


def _json_list(text: str) -> list[dict]:
    data = json.loads(text)
    assert isinstance(data, list)
    return data


def _material_id_by_name(bridge: WorkbenchBridge, material_name: str) -> str:
    for option in bridge.materialOptions:
        material_id, _, label = option.partition("|")
        if material_name in label:
            return material_id.strip()
    raise AssertionError(f"material {material_name!r} not found in {bridge.materialOptions}")


def _build_two_disjoint_rectangles(bridge: WorkbenchBridge) -> None:
    coordinates = [
        (0.0, 0.0),
        (2.0, 0.0),
        (2.0, 1.0),
        (0.0, 1.0),
        (3.0, 0.0),
        (4.5, 0.0),
        (4.5, 1.0),
        (3.0, 1.0),
    ]
    for x, y in coordinates:
        assert bridge.addModelPoint(x, y), bridge.statusText

    point_ids = [row["id"] for row in _json_list(bridge.modelPointsJson)]
    left = point_ids[:4]
    right = point_ids[4:]
    edges = [
        (left[0], left[1]),
        (left[1], left[2]),
        (left[2], left[3]),
        (left[3], left[0]),
        (right[0], right[1]),
        (right[1], right[2]),
        (right[2], right[3]),
        (right[3], right[0]),
    ]
    for start_id, end_id in edges:
        assert bridge.connectModelEdge(start_id, end_id), bridge.statusText

    assert bridge.buildModelFaces(), bridge.statusText


def test_stage18_multiple_faces_material_assignment_preview_and_json() -> None:
    bridge = WorkbenchBridge()
    assert bridge.newProject(), bridge.statusText
    _build_two_disjoint_rectangles(bridge)

    faces = _json_list(bridge.modelFacesJson)
    assert [row["id"] for row in faces] == ["f1", "f2"]

    assert bridge.addMaterial("aluminum", 70_000_000_000.0, 0.33, "#A8C5E6"), bridge.statusText

    steel_id = _material_id_by_name(bridge, "steel")
    aluminum_id = _material_id_by_name(bridge, "aluminum")

    assert bridge.selectGeometryFace("f1"), bridge.statusText
    assert bridge.assignMaterialToSelectedFace(steel_id, 0.01), bridge.statusText
    assert bridge.selectGeometryFace("f2"), bridge.statusText
    assert bridge.assignMaterialToSelectedFace(aluminum_id, 0.02), bridge.statusText

    rows = _json_list(bridge.faceMaterialJson)
    rows_by_face = {row["face_id"]: row for row in rows}
    assert rows_by_face["f1"]["material_name"] == "steel"
    assert rows_by_face["f1"]["source"] == "face"
    assert rows_by_face["f1"]["thickness"] == 0.01
    assert rows_by_face["f2"]["material_name"] == "aluminum"
    assert rows_by_face["f2"]["source"] == "face"
    assert rows_by_face["f2"]["thickness"] == 0.02
    assert "f1 | steel" in bridge.faceMaterialRowsPreview
    assert "f2 | aluminum" in bridge.faceMaterialRowsPreview

from __future__ import annotations

import json

import pytest

from ui.backend.workbench_bridge import WorkbenchBridge


def _json_list(text: str) -> list[dict]:
    data = json.loads(text)
    assert isinstance(data, list)
    return data


@pytest.mark.integration
def test_stage18_bridge_face_selection_shared_edge_rectangles() -> None:
    bridge = WorkbenchBridge()
    assert bridge.newProject(), bridge.statusText

    for x, y in ((0.0, 0.0), (1.0, 0.0), (2.0, 0.0), (0.0, 1.0), (1.0, 1.0), (2.0, 1.0)):
        assert bridge.addModelPoint(x, y), bridge.statusText

    point_ids = [point["id"] for point in _json_list(bridge.modelPointsJson)]
    p1, p2, p3, p4, p5, p6 = point_ids
    for start_id, end_id in (
        (p1, p2),
        (p2, p5),
        (p5, p4),
        (p4, p1),
        (p2, p3),
        (p3, p6),
        (p6, p5),
    ):
        assert bridge.connectModelEdge(start_id, end_id), bridge.statusText

    assert bridge.buildModelFaces(), bridge.statusText
    assert bridge.modelFaceCount == 2

    faces = _json_list(bridge.modelFacesJson)
    assert all(face.get("point_ids") for face in faces)

    assert bridge.selectGeometryFace("f1"), bridge.statusText
    assert bridge.selectedFaceId == "f1"
    assert bridge.selectedGeometryType == "face"
    assert bridge.selectedGeometryId == "f1"

    assert bridge.selectGeometryFace("f2"), bridge.statusText
    assert bridge.selectedFaceId == "f2"
    assert bridge.selectedGeometryType == "face"
    assert bridge.selectedGeometryId == "f2"


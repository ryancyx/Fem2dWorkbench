from __future__ import annotations

import json

import pytest

from ui.backend.workbench_bridge import WorkbenchBridge


def _json_list(text: str) -> list[dict]:
    data = json.loads(text)
    assert isinstance(data, list)
    return data


@pytest.mark.integration
def test_stage18_gui_like_two_faces_build_workflow() -> None:
    bridge = WorkbenchBridge()
    assert bridge.newProject(), bridge.statusText

    for x, y in (
        (0.0, 0.0),
        (1.0, 0.0),
        (1.0, 1.0),
        (0.0, 1.0),
        (2.0, 0.0),
        (3.0, 0.0),
        (3.0, 1.0),
        (2.0, 1.0),
    ):
        assert bridge.addModelPoint(x, y), bridge.statusText

    point_ids = [point["id"] for point in _json_list(bridge.modelPointsJson)]
    left = point_ids[:4]
    right = point_ids[4:]

    for start_id, end_id in (
        (left[0], left[1]),
        (left[1], left[2]),
        (left[2], left[3]),
        (left[3], left[0]),
        (right[0], right[1]),
        (right[1], right[2]),
        (right[2], right[3]),
        (right[3], right[0]),
    ):
        assert bridge.connectModelEdge(start_id, end_id), bridge.statusText

    assert bridge.buildModelFaces(), bridge.statusText
    assert bridge.modelFaceCount == 2
    assert "已生成 2 个闭合面" in bridge.statusText

    faces = _json_list(bridge.modelFacesJson)
    assert [face["id"] for face in faces] == ["f1", "f2"]
    assert all(len(face["edge_ids"]) == 4 for face in faces)


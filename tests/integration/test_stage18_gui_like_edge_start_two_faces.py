from __future__ import annotations

import json

import pytest

from ui.backend.workbench_bridge import WorkbenchBridge


def _json_list(text: str) -> list[dict]:
    data = json.loads(text)
    assert isinstance(data, list)
    return data


@pytest.mark.integration
def test_stage18_gui_like_edge_start_two_faces() -> None:
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
        assert bridge.selectGeometryPoint(start_id), bridge.statusText
        assert bridge.startEdgeFromSelectedPoint(), bridge.statusText
        assert bridge.edgeStartPointId == start_id
        assert bridge.connectEdgeToPoint(end_id), bridge.statusText
        assert bridge.edgeStartPointId == ""

    assert bridge.buildModelFaces(), bridge.statusText
    assert bridge.modelFaceCount == 2
    assert "已生成 2 个闭合面" in bridge.statusText


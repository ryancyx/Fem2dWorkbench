from __future__ import annotations

import json

import pytest

from ui.backend.workbench_bridge import WorkbenchBridge


def _json_list(text: str) -> list[dict]:
    data = json.loads(text)
    assert isinstance(data, list)
    return data


@pytest.mark.integration
def test_stage18_shared_faces_after_normalization() -> None:
    bridge = WorkbenchBridge()
    assert bridge.newProject(), bridge.statusText

    for x, y in ((0.0, 0.0), (1.0, 0.0), (2.0, 0.0), (0.0, 1.0), (1.0, 1.0), (2.0, 1.0)):
        assert bridge.addModelPoint(x, y), bridge.statusText
    point_ids = [row["id"] for row in _json_list(bridge.modelPointsJson)]
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

    original_edge_count = len(_json_list(bridge.modelEdgesJson))

    assert bridge.buildModelFaces(), bridge.statusText
    assert bridge.modelFaceCount == 2
    assert bridge.statusText == "已生成 2 个闭合面"
    assert len(_json_list(bridge.modelEdgesJson)) == original_edge_count

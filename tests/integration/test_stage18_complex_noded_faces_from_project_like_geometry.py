from __future__ import annotations

import json

import pytest

from ui.backend.workbench_bridge import WorkbenchBridge


def _json_list(text: str) -> list[dict]:
    data = json.loads(text)
    assert isinstance(data, list)
    return data


def _point_ids(bridge: WorkbenchBridge) -> list[str]:
    return [row["id"] for row in _json_list(bridge.modelPointsJson)]


@pytest.mark.integration
def test_stage18_complex_noded_faces_from_project_like_geometry() -> None:
    bridge = WorkbenchBridge()
    assert bridge.newProject(), bridge.statusText

    for x, y in (
        (0.0, 0.0),
        (6.0, 0.0),
        (6.0, 4.0),
        (0.0, 4.0),
        (2.0, 0.0),
        (2.0, 4.0),
    ):
        assert bridge.addModelPoint(x, y), bridge.statusText

    p1, p2, p3, p4, p5, p6 = _point_ids(bridge)
    for start_id, end_id in (
        (p1, p2),
        (p2, p3),
        (p3, p4),
        (p4, p1),
        (p5, p6),
    ):
        assert bridge.connectModelEdge(start_id, end_id), bridge.statusText

    original_edge_count = len(_json_list(bridge.modelEdgesJson))

    assert bridge.buildModelFaces(), bridge.statusText
    assert bridge.modelFaceCount == 2
    assert "已自动拆分 2 条边" in bridge.statusText

    edge_rows = _json_list(bridge.modelEdgesJson)
    assert len(edge_rows) == original_edge_count + 2
    point_pairs = {
        frozenset((row["start_point_id"], row["end_point_id"]))
        for row in edge_rows
    }
    assert frozenset((p1, p5)) in point_pairs
    assert frozenset((p5, p2)) in point_pairs
    assert frozenset((p4, p6)) in point_pairs
    assert frozenset((p6, p3)) in point_pairs


@pytest.mark.integration
def test_stage18_complex_noded_open_chain_reports_remaining_open_issue() -> None:
    bridge = WorkbenchBridge()
    assert bridge.newProject(), bridge.statusText

    for x, y in (
        (0.0, 0.0),
        (6.0, 0.0),
        (6.0, 4.0),
        (0.0, 4.0),
        (2.0, 0.0),
        (2.0, -2.0),
    ):
        assert bridge.addModelPoint(x, y), bridge.statusText

    p1, p2, p3, p4, p5, p6 = _point_ids(bridge)
    for start_id, end_id in (
        (p1, p2),
        (p2, p3),
        (p3, p4),
        (p4, p1),
        (p5, p6),
    ):
        assert bridge.connectModelEdge(start_id, end_id), bridge.statusText

    assert not bridge.buildModelFaces()
    assert "未参与成面的边" in bridge.statusText or "dangles" in bridge.statusText or "cuts" in bridge.statusText

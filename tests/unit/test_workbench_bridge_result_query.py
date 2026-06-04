from __future__ import annotations

from ui.backend.workbench_bridge import WorkbenchBridge


def test_bridge_query_result_for_rectangle_model():
    bridge = WorkbenchBridge()

    assert bridge.createDefaultProject(2.0, 1.0, 210e9, 0.3, 0.01, -1000.0)
    assert bridge.solveCurrentModel()
    assert bridge.queryResultAtPoint(1.0, 0.5)

    assert bridge.resultQueryText != ""
    assert "查询点" in bridge.resultQueryText
    assert "最近节点" in bridge.resultQueryText


def test_bridge_query_result_fails_without_solution():
    bridge = WorkbenchBridge()

    assert bridge.newProject()
    assert bridge.queryResultAtPoint(0.0, 0.0) is False
    assert "请先完成求解" in bridge.statusText

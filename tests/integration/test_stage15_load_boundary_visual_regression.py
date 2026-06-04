from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAIN_WORKBENCH_QML = PROJECT_ROOT / "ui" / "qml" / "MainWorkbench.qml"


def test_stage15_qml_contains_material_fill_and_load_visual_helpers():
    qml_text = MAIN_WORKBENCH_QML.read_text(encoding="utf-8")

    required_snippets = [
        "function materialFillColor",
        "bridge.activePartMaterialColor",
        "function drawArrowToTarget",
        "function drawDistributedLoadOnEdge",
        "function selectNearestBoundaryTargetByCoordinates",
        "function selectNearestLoadTargetByCoordinates",
        "text: \"当前版本会按输入坐标吸附到最近几何点或几何边，再作为约束目标。\"",
        "text: \"当前版本会按输入坐标吸附到最近几何点或几何边，再作为载荷目标。\"",
    ]

    for snippet in required_snippets:
        assert snippet in qml_text

from __future__ import annotations

from pathlib import Path


QML = Path(__file__).resolve().parents[2] / "ui" / "qml" / "MainWorkbench.qml"


def test_stage15_qml_contains_result_visualization_and_query_controls():
    text = QML.read_text(encoding="utf-8")

    for snippet in (
        "显示变形图",
        "显示 Von Mises 云图",
        "查询结果",
        "查询 X",
        "查询 Y",
        "resultDialog",
        "deformationDialog",
        "导出全部结果",
        "bridge.queryResultAtPoint",
    ):
        assert snippet in text

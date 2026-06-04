from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAIN_WORKBENCH_QML = PROJECT_ROOT / "ui" / "qml" / "MainWorkbench.qml"


def test_stage15_qml_contains_visualization_and_query_entries():
    qml_text = MAIN_WORKBENCH_QML.read_text(encoding="utf-8")

    required_snippets = [
        'text: "显示变形图"',
        'text: "显示 Von Mises 应力云图"',
        'text: "任意点结果查询"',
        'text: "查询结果"',
        'text: "按坐标选择目标"',
        'title: "求解完成"',
        'text: "查看结果"',
        'text: "输出 / 状态日志"',
        'text: "导出结果"',
    ]

    for snippet in required_snippets:
        assert snippet in qml_text

    assert 'title: "求解"; desc:' not in qml_text
    assert "DockPanel {" not in qml_text


def test_stage15_qml_hides_stage13_validation_entries_from_visible_ui():
    qml_text = MAIN_WORKBENCH_QML.read_text(encoding="utf-8")

    forbidden_visible_snippets = [
        'text: "求解草图"',
        'placeholderText: "固定边 ID"',
        'placeholderText: "载荷边 ID"',
        'text: "设为固定边"',
        'text: "设为载荷边"',
    ]

    for snippet in forbidden_visible_snippets:
        assert snippet not in qml_text

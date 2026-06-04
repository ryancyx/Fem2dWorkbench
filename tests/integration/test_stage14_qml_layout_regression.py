from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAIN_WORKBENCH_QML = PROJECT_ROOT / "ui" / "qml" / "MainWorkbench.qml"


def test_stage14_qml_contains_engineering_workflow_entries():
    qml_text = MAIN_WORKBENCH_QML.read_text(encoding="utf-8")

    required_snippets = [
        "进入编辑模式",
        "退出编辑模式",
        "节点列表",
        "边列表",
        "材料管理器",
        "应用材料",
        "生成网格",
        "网格质量摘要",
        "添加约束",
        "添加载荷",
        "求解",
        "当前模块面板",
        "当前目标",
        "固定 Ux",
        "固定 Uy",
        "nodal_concentrated",
        "edge_uniform",
        "查看 / 编辑属性",
        "对象属性",
        "新建二维零件",
        "新建空零件面",
        "求解结果",
        "二维零件闭合面建模",
        "输出 / 状态日志",
    ]

    for snippet in required_snippets:
        assert snippet in qml_text, f"Missing stage 14 QML snippet: {snippet}"

    forbidden_visible_entries = [
        'text: "新增矩形零件"',
        'text: "新增草图零件"',
        'text: "求解草图"',
        'placeholderText: "固定边 ID"',
        'placeholderText: "载荷边 ID"',
        "参数化矩形零件",
    ]
    for snippet in forbidden_visible_entries:
        assert snippet not in qml_text, f"Outdated validation UI still visible: {snippet}"

    assert '\\"' not in qml_text

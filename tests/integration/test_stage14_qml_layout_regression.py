from __future__ import annotations

from pathlib import Path


QML = Path(__file__).resolve().parents[2] / "ui" / "qml" / "MainWorkbench.qml"


def test_stage14_qml_layout_reflects_single_model_workflow():
    text = QML.read_text(encoding="utf-8")

    required = [
        'model: ["建模与材料", "网格生成", "约束与载荷", "求解结果"]',
        "建模工具",
        "材料分配",
        "网格生成",
        "唯一正式网格器：Gmsh CST 三角网格",
        "约束与载荷",
        "添加集中力",
        "添加均布载荷",
        "求解当前模型",
        "显示变形图",
        "显示 Von Mises 云图",
        "导出全部结果",
    ]
    for snippet in required:
        assert snippet in text

    forbidden = [
        'text: "零件"',
        'text: "属性"',
        'text: "装配"',
        'text: "实例"',
    ]
    for snippet in forbidden:
        assert snippet not in text

from __future__ import annotations

from pathlib import Path


QML = Path(__file__).resolve().parents[2] / "ui" / "qml" / "MainWorkbench.qml"


def test_stage16_qml_contains_material_and_assembly_controls():
    text = QML.read_text(encoding="utf-8")

    for snippet in (
        "materialEditorDialog",
        "材料编辑器",
        "打开材料编辑器",
        "应用到闭合面",
        "应用到整个零件",
        "创建实例",
        "移动模式",
        "移动参考点到坐标",
    ):
        assert snippet in text
    assert "虚线矩形占位" not in text


def test_stage16_qml_draws_load_layer_after_selection_and_uses_larger_arrows():
    text = QML.read_text(encoding="utf-8")
    assert text.rfind("root.drawLoadLayer(ctx)") > text.rfind("root.drawSelectionLayer(ctx)")
    assert "var arrowSize = 10" in text
    assert "root.drawArrowToTarget(ctx, lp.x, lp.y, load.qx, load.qy, 35)" in text
    assert "root.drawArrowToTarget(ctx, headX, headY, qx, qy, 28)" in text

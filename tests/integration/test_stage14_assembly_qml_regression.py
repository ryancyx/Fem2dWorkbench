from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAIN_WORKBENCH_QML = PROJECT_ROOT / "ui" / "qml" / "MainWorkbench.qml"


def test_stage14_assembly_and_material_qml_entries_are_explicit():
    qml_text = MAIN_WORKBENCH_QML.read_text(encoding="utf-8")

    required_snippets = [
        "新建二维零件",
        "应用目标零件",
        "bridge.assignMaterialToPart",
        "装配实例编辑",
        "bridge.addInstanceForPart",
        "bridge.instanceOptions",
        "resultDialog",
        "求解结果",
    ]
    for snippet in required_snippets:
        assert snippet in qml_text

    draw_base_geometry_block = qml_text.split("function drawBaseGeometry", 1)[1].split("function drawSketchGeometry", 1)[0]
    assert "setLineDash([8, 6])" not in draw_base_geometry_block
    assert "strokeRect(root.lastPlateX - 32" not in draw_base_geometry_block

from __future__ import annotations

from pathlib import Path


QML = Path(__file__).resolve().parents[2] / "ui" / "qml" / "MainWorkbench.qml"


def test_stage16_qml_confirms_assembly_ui_has_been_removed():
    text = QML.read_text(encoding="utf-8")

    forbidden = [
        "function assemblyInstances()",
        "function drawAssemblyGeometry(ctx)",
        "function drawAssemblyInstance(ctx, instanceRow)",
        "JSON.parse(bridge.assemblyInstancesJson)",
        "bridge.addInstanceForPart(",
        "bridge.setActiveInstance(",
        "bridge.moveActiveInstance(",
        "bridge.moveActiveInstanceReferencePointTo(",
        "bridge.deleteActiveInstance()",
        "activeInstanceCombo",
        "instanceOptions",
        "assemblyInstancesJson",
        "activeInstanceTx",
        "activeInstanceTy",
        "装配",
        "实例",
    ]
    for snippet in forbidden:
        assert snippet not in text


def test_stage16_qml_uses_single_model_navigation_and_repaint_chain():
    text = QML.read_text(encoding="utf-8")

    required = [
        "建模与材料",
        "网格生成",
        "约束与载荷",
        "求解结果",
        "root.repaintViewport()",
        "bridge.setModelTool(",
        "bridge.generateMesh(",
        "bridge.solveCurrentModel()",
    ]
    for snippet in required:
        assert snippet in text

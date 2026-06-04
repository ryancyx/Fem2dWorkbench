from __future__ import annotations

from pathlib import Path


QML = Path(__file__).resolve().parents[2] / "ui" / "qml" / "MainWorkbench.qml"


def test_stage16_qml_contains_multi_instance_assembly_rendering():
    text = QML.read_text(encoding="utf-8")

    assert "function assemblyInstances()" in text
    assert "function drawAssemblyGeometry(ctx)" in text
    assert "function drawAssemblyInstance(ctx, instanceRow)" in text
    assert "JSON.parse(bridge.assemblyInstancesJson)" in text
    assert "for (var i = 0; i < rows.length; i++)" in text
    assert "root.drawAssemblyInstance(ctx, rows[i])" in text
    assert "暂无装配实例，请选择零件并创建实例" in text


def test_stage16_qml_does_not_only_depend_on_active_instance_offsets_for_assembly_draw():
    text = QML.read_text(encoding="utf-8")

    assert "px += bridge.activeInstanceTx * 80 * root.viewportScale" not in text
    assert "py -= bridge.activeInstanceTy * 80 * root.viewportScale" not in text
    assert '"points": instanceRow.points' not in text
    assert "instanceRow.points || []" in text
    assert "instanceRow.tx" in text
    assert "instanceRow.ty" in text


def test_stage16_qml_material_target_combo_switches_active_part_and_repaints():
    text = QML.read_text(encoding="utf-8")

    assert "id: materialTargetPartCombo" in text
    assert "bridge.setActivePart(partId)" in text
    assert "root.clearViewportSelection()" in text
    assert "root.clearBridgeSelectionIfNeeded()" in text
    assert "root.repaintViewport()" in text


def test_stage16_qml_instance_controls_repaint_after_actions():
    text = QML.read_text(encoding="utf-8")

    assert "id: activeInstanceCombo" in text
    assert "bridge.setActiveInstance(instanceId)" in text
    assert "bridge.addInstanceForPart(" in text
    assert "bridge.moveActiveInstance(Number(moveTxField.text), Number(moveTyField.text))" in text
    assert "bridge.moveActiveInstanceReferencePointTo(" in text
    assert "bridge.deleteActiveInstance()" in text
    assert text.count("root.repaintViewport()") >= 5

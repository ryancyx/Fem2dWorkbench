from __future__ import annotations

from pathlib import Path


def test_stage18_qml_face_combo_regression() -> None:
    qml_path = Path("ui/qml/MainWorkbench.qml")
    text = qml_path.read_text(encoding="utf-8")

    assert "id: faceTargetCombo" in text
    assert "目标闭合面" in text
    assert "function parseFaceIdFromOption" in text
    assert "function faceOptionsFromJson" in text
    assert "bridge.selectGeometryFace(faceId)" in text
    assert "bridge.assignMaterialToSelectedFace(" in text
    assert "应用到选中闭合面" in text
    assert "请先生成闭合面" in text or "请先生成并选择闭合面" in text


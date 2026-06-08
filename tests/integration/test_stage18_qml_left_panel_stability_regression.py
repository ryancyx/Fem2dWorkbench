from __future__ import annotations

from pathlib import Path


def test_stage18_qml_left_panel_stability_regression() -> None:
    text = Path("ui/qml/MainWorkbench.qml").read_text(encoding="utf-8", errors="ignore")

    assert "id: leftPanelScroll" in text
    assert "Layout.minimumWidth: root.leftPanelWidth" in text
    assert "Layout.maximumWidth: root.leftPanelWidth" in text
    assert "id: rightPanelScroll" in text
    assert "Layout.minimumWidth: root.rightPanelWidth" in text
    assert "Layout.maximumWidth: root.rightPanelWidth" in text
    assert "focusPolicy: Qt.NoFocus" in text
    assert "anchors.fill: root" not in text
    assert "leftPanelVisible" not in text
    assert "rightPanelVisible" not in text
    assert "resizeStartLeftWidth" not in text
    assert "resizeStartRightWidth" not in text
    assert "function resizeLeftPanelBy" not in text
    assert "function resizeRightPanelBy" not in text

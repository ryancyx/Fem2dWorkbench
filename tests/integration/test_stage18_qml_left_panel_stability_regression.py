from __future__ import annotations

from pathlib import Path


def test_stage18_qml_left_panel_stability_regression() -> None:
    text = Path("ui/qml/MainWorkbench.qml").read_text(encoding="utf-8", errors="ignore")

    assert "id: leftPanelScroll" in text
    assert "Layout.preferredWidth: root.leftPanelWidth" in text
    assert "Layout.minimumWidth: root.leftPanelWidth" in text
    assert "Layout.maximumWidth: root.leftPanelWidth" in text
    assert "Layout.fillHeight: true" in text
    assert "clip: true" in text
    assert "id: rightPanelScroll" in text
    assert "Layout.minimumWidth: root.rightPanelWidth" in text
    assert "Layout.maximumWidth: root.rightPanelWidth" in text
    assert "focusPolicy: Qt.NoFocus" in text
    assert 'Layout.preferredHeight: 88' in text
    assert 'Layout.preferredHeight: 126' in text
    assert 'Layout.preferredHeight: 56' in text
    assert 'maximumLineCount: 2' in text
    assert 'text: selectedObjectDescription' not in text
    assert 'text: "状态：" + bridge.statusText' not in text
    assert 'bottomStatusPrimaryText()' in text
    assert 'bottomStatusSecondaryText()' in text
    assert 'shortSelectionDetailText()' in text
    assert 'function handleViewportClick' in text
    assert 'function handleModelingClick' in text
    assert 'function handleTargetSelectionClick' in text
    assert 'leftPanelWidth =' not in text
    assert 'leftPanelVisible' not in text
    assert "anchors.fill: root" not in text
    assert "rightPanelVisible" not in text
    assert "resizeStartLeftWidth" not in text
    assert "resizeStartRightWidth" not in text
    assert "function resizeLeftPanelBy" not in text
    assert "function resizeRightPanelBy" not in text
    assert "resizeStartMouseX" not in text

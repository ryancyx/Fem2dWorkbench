from __future__ import annotations

from pathlib import Path


def test_stage18_qml_view_pan_regression() -> None:
    text = Path("ui/qml/MainWorkbench.qml").read_text(encoding="utf-8")

    assert "移动视图" in text
    assert "property bool viewportPanMode" in text
    assert "property bool isPanningViewport" in text
    assert "property real viewportOffsetX" in text
    assert "property real viewportOffsetY" in text
    assert "root.viewportOffsetX = root.panStartOffsetX + (mouse.x - root.panStartMouseX)" in text
    assert "root.viewportOffsetY = root.panStartOffsetY + (mouse.y - root.panStartMouseY)" in text
    assert "if (root.viewportPanMode && mouse.button === Qt.LeftButton)" in text
    assert "if (root.viewportPanMode) {" in text
    assert "root.handleViewportClick(mouse.x, mouse.y)" in text
    assert "root.repaintViewport()" in text


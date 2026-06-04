from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAIN_WORKBENCH_QML = PROJECT_ROOT / "ui" / "qml" / "MainWorkbench.qml"


def test_stage14_panel_resize_qml_regression():
    qml_text = MAIN_WORKBENCH_QML.read_text(encoding="utf-8")

    required_snippets = [
        "PanelResizeHandle",
        "splitterWidth",
        "resizeLeftPanelBy",
        "resizeRightPanelBy",
        "clampPanelWidths",
        "availableWorkspaceWidth",
        "mainWorkspaceRow",
        "minCenterPanelWidth",
        "mouseXInWorkspace",
        "ScrollBar.vertical.policy: ScrollBar.AlwaysOff",
        "ScrollBar.horizontal.policy: ScrollBar.AlwaysOff",
        "leftPanelResizeHandle",
        "rightPanelResizeHandle",
    ]

    for snippet in required_snippets:
        assert snippet in qml_text, f"Missing panel resize QML snippet: {snippet}"

    forbidden_snippets = [
        "leftResizeHandle",
        "leftResizeMouseArea",
        "rightResizeHandle",
        "rightResizeMouseArea",
        '\\\\"',
    ]

    for snippet in forbidden_snippets:
        assert snippet not in qml_text, f"Legacy or invalid snippet should be removed: {snippet}"

    assert qml_text.count("ScrollBar.vertical.policy: ScrollBar.AlwaysOff") >= 2
    assert qml_text.count("ScrollBar.horizontal.policy: ScrollBar.AlwaysOff") >= 2

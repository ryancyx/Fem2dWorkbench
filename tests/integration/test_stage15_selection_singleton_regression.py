from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAIN_WORKBENCH_QML = PROJECT_ROOT / "ui" / "qml" / "MainWorkbench.qml"


def test_stage15_qml_contains_single_selection_helpers():
    qml_text = MAIN_WORKBENCH_QML.read_text(encoding="utf-8")

    assert "function clearViewportSelection()" in qml_text
    assert "selectedObjectType" in qml_text
    assert "selectedObjectName" in qml_text
    assert "selectedObjectDescription" in qml_text
    assert "function syncSelectionSummary()" in qml_text
    assert "root.clearViewportSelection()" in qml_text
    assert "root.repaintViewport()" in qml_text


def test_stage15_target_selection_handlers_do_not_select_faces_for_loads_or_constraints():
    qml_text = MAIN_WORKBENCH_QML.read_text(encoding="utf-8")

    target_start = qml_text.index("function handleTargetSelectionClick")
    query_start = qml_text.index("function handleResultQueryClick")
    target_block = qml_text[target_start:query_start]

    assert "findFaceAt" not in target_block
    assert "bridge.selectGeometryFace" not in target_block

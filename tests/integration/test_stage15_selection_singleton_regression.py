from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAIN_WORKBENCH_QML = PROJECT_ROOT / "ui" / "qml" / "MainWorkbench.qml"


def test_stage15_qml_contains_single_selection_helpers():
    qml_text = MAIN_WORKBENCH_QML.read_text(encoding="utf-8")

    assert "function clearViewportSelection()" in qml_text
    assert "function selectOnlyPoint(pointId, description)" in qml_text
    assert "function selectOnlyEdge(edgeId, description)" in qml_text
    assert "function selectOnlyFace(faceId, description)" in qml_text
    assert "root.clearViewportSelection()" in qml_text
    assert "root.repaintViewport()" in qml_text


def test_stage15_qml_boundary_and_load_handlers_do_not_select_faces():
    qml_text = MAIN_WORKBENCH_QML.read_text(encoding="utf-8")

    boundary_start = qml_text.index("function handleBoundaryViewportClick")
    load_start = qml_text.index("function handleLoadViewportClick")
    readonly_start = qml_text.index("function handleReadonlyViewportPick")
    boundary_block = qml_text[boundary_start:load_start]
    load_block = qml_text[load_start:readonly_start]

    assert "findSketchFaceAt" not in boundary_block
    assert "findSketchFaceAt" not in load_block

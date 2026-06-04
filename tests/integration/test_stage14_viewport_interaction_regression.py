from __future__ import annotations

from pathlib import Path
import re


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAIN_WORKBENCH_QML = PROJECT_ROOT / "ui" / "qml" / "MainWorkbench.qml"


def _extract_function(qml_text: str, name: str) -> str:
    marker = f"function {name}("
    start = qml_text.index(marker)
    brace_start = qml_text.index("{", start)
    depth = 0
    for index in range(brace_start, len(qml_text)):
        char = qml_text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return qml_text[start:index + 1]
    raise AssertionError(f"Failed to extract function body: {name}")


def test_stage14_viewport_mode_routing_is_decoupled():
    qml_text = MAIN_WORKBENCH_QML.read_text(encoding="utf-8")

    assert "function switchMode" in qml_text
    assert "function handleViewportClick" in qml_text
    assert "function handlePartEditViewportClick" in qml_text
    assert "function handleBoundaryViewportClick" in qml_text
    assert "function handleLoadViewportClick" in qml_text
    assert "function handleReadonlyViewportPick" in qml_text
    assert "function setViewportSelection" in qml_text
    assert "function setViewportHint" in qml_text
    assert "selectedSketchFaceId" in qml_text
    assert "function orderedSketchFaceScreenPolygon" in qml_text
    assert "function pointInPolygon" in qml_text
    assert "function findSketchFaceAt" in qml_text
    assert "function selectSketchFace" in qml_text
    assert "id: objectPropertyDialog" in qml_text
    assert "id: resultDialog" in qml_text

    for handler in [
        "handleViewportClick",
        "handlePartEditViewportClick",
        "handleBoundaryViewportClick",
        "handleLoadViewportClick",
        "handleReadonlyViewportPick",
    ]:
        body = _extract_function(qml_text, handler)
        assert re.search(r"\broot\.currentMode\s*=(?!=)", body) is None
        assert re.search(r"(?<!\.)\bcurrentMode\s*=(?!=)", body) is None
        assert "switchMode(" not in body

    switch_mode_body = _extract_function(qml_text, "switchMode")
    assert "currentMode = modeName" in switch_mode_body

    readonly_body = _extract_function(qml_text, "handleReadonlyViewportPick")
    assert "findSketchFaceAt" in readonly_body

    face_select_body = _extract_function(qml_text, "selectSketchFace")
    assert '"face"' in face_select_body
    assert "闭合二维面" in face_select_body

    boundary_body = _extract_function(qml_text, "handleBoundaryViewportClick")
    assert "findSketchFaceAt" not in boundary_body
    load_body = _extract_function(qml_text, "handleLoadViewportClick")
    assert "findSketchFaceAt" not in load_body

    assert "onClicked: root.selectByMode(" in qml_text
    assert "root.handleViewportClick(mouse.x, mouse.y)" in qml_text
    assert "root.selectOnlyPoint(pointId, \"节点\")" in qml_text
    assert "root.selectOnlyEdge(edgeId, \"边\")" in qml_text

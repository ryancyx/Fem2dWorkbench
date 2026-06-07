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

    assert "function handleViewportClick" in qml_text
    assert "function handleModelingClick" in qml_text
    assert "function handleTargetSelectionClick" in qml_text
    assert "function handleResultQueryClick" in qml_text
    assert "function handleViewportSelection" in qml_text
    assert "function pointInPolygon" in qml_text
    assert "function findFaceAt" in qml_text
    assert "id: resultDialog" in qml_text
    assert "id: deformationDialog" in qml_text

    for handler in [
        "handleViewportClick",
        "handleModelingClick",
        "handleTargetSelectionClick",
        "handleResultQueryClick",
    ]:
        body = _extract_function(qml_text, handler)
        assert re.search(r"\broot\.currentMode\s*=(?!=)", body) is None
        assert re.search(r"(?<!\.)\bcurrentMode\s*=(?!=)", body) is None

    click_body = _extract_function(qml_text, "handleViewportClick")
    assert 'currentMode === "建模与材料"' in click_body
    assert 'currentMode === "约束与载荷"' in click_body
    assert 'currentMode === "求解结果"' in click_body

    target_body = _extract_function(qml_text, "handleTargetSelectionClick")
    assert "findFaceAt" not in target_body
    assert "bridge.selectGeometryPoint" in target_body
    assert "bridge.selectGeometryEdge" in target_body

    query_body = _extract_function(qml_text, "handleResultQueryClick")
    assert "bridge.queryResultAtPoint" in query_body

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAIN_WORKBENCH_QML = PROJECT_ROOT / "ui" / "qml" / "MainWorkbench.qml"


def test_stage14_viewport_render_pipeline_is_structured():
    qml_text = MAIN_WORKBENCH_QML.read_text(encoding="utf-8")

    required_snippets = [
        "function clearViewportCanvas",
        "ctx.setTransform(1, 0, 0, 1, 0, 0)",
        "ctx.clearRect(0, 0, modelCanvas.width, modelCanvas.height)",
        "function drawViewportBackground",
        "function shouldDrawMesh",
        "function shouldDrawBoundary",
        "function shouldDrawLoad",
        "function shouldDrawResult",
        "function repaintViewport",
        "function clearTransientViewportStateForMode",
        "function drawSelectedSketchFace",
        "function onSketchChanged()",
        "function onSketchMeshChanged()",
        "function onProjectChanged()",
        "function onResultChanged()",
        "root.clearViewportCanvas(ctx)",
        "root.drawViewportBackground(ctx)",
        "root.drawBaseGeometry(ctx)",
        "root.drawMeshLayer(ctx)",
        "root.drawBoundaryLayer(ctx)",
        "root.drawLoadLayer(ctx)",
        "root.drawResultLayer(ctx)",
        "root.drawSelectionLayer(ctx)",
        "root.drawSelectedSketchFace(ctx)",
        "二维网格",
    ]

    for snippet in required_snippets:
        assert snippet in qml_text, f"Missing viewport render snippet: {snippet}"

    forbidden_snippets = [
        '\\"',
        'text: "新增矩形零件"',
        'text: "新增草图零件"',
        "参数化矩形零件",
    ]
    for snippet in forbidden_snippets:
        assert snippet not in qml_text

    assert "root.edgeQy" not in qml_text.split("function drawLoadLayer", 1)[1].split("function drawResultLayer", 1)[0]
    assert 'currentMode === "边界"' not in qml_text.split("function drawBoundaryLayer", 1)[1].split("function drawLoadLayer", 1)[0]
    assert 'currentMode === "载荷"' not in qml_text.split("function drawLoadLayer", 1)[1].split("function drawResultLayer", 1)[0]

    selected_face_body = qml_text.split("function drawSelectedSketchFace", 1)[1].split("function drawSelectionLayer", 1)[0]
    assert "selectedSketchFaceId" in selected_face_body
    assert "bridge.sketchHasFace" in selected_face_body
    assert 'rgba(37, 99, 235, 0.22)' in selected_face_body

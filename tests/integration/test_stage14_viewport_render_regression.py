from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAIN_WORKBENCH_QML = PROJECT_ROOT / "ui" / "qml" / "MainWorkbench.qml"


def test_stage14_viewport_render_pipeline_is_structured():
    qml_text = MAIN_WORKBENCH_QML.read_text(encoding="utf-8")

    required_snippets = [
        "function clearViewportCanvas",
        "ctx.setTransform(1, 0, 0, 1, 0, 0)",
        "ctx.clearRect(0, 0, viewport.width, viewport.height)",
        "function drawViewportBackground",
        "function repaintViewport",
        "function drawModelGeometry",
        "function drawMeshLayer",
        "function drawBoundaryLayer",
        "function drawResultLayer",
        "function drawQueryPointLayer",
        "function drawLoadLayer",
        "function drawSelectionLayer",
        "root.clearViewportCanvas(ctx)",
        "root.drawViewportBackground(ctx)",
        "root.drawModelGeometry(ctx)",
        "root.drawMeshLayer(ctx)",
        "root.drawBoundaryLayer(ctx)",
        "root.drawResultLayer(ctx)",
        "root.drawQueryPointLayer(ctx)",
        "root.drawLoadLayer(ctx)",
        "root.drawSelectionLayer(ctx)",
        "function onSketchChanged()",
        "function onSketchMeshChanged()",
        "function onProjectChanged()",
        "function onResultChanged()",
        "function onSketchChanged() { root.onSketchChanged() }",
        "function onSketchMeshChanged() { root.onSketchMeshChanged() }",
        "function onProjectChanged() { root.onProjectChanged() }",
        "function onResultChanged() { root.onResultChanged() }",
    ]

    for snippet in required_snippets:
        assert snippet in qml_text, f"Missing viewport render snippet: {snippet}"

    forbidden_snippets = [
        'text: "新增矩形零件"',
        'text: "新增草图零件"',
        "assemblyInstancesJson",
        "drawAssemblyGeometry",
        "drawAssemblyInstance",
    ]
    for snippet in forbidden_snippets:
        assert snippet not in qml_text

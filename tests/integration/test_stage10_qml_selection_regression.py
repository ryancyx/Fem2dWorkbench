from pathlib import Path


def test_stage10_qml_selection_regression():
    qml = Path("ui/qml/MainWorkbench.qml").read_text(encoding="utf-8")

    expected_snippets = [
        "selectedObjectType",
        "selectedObjectName",
        "selectedObjectDescription",
        "lastPlateX",
        "lastPlateY",
        "lastPlateW",
        "lastPlateH",
        "function selectObject",
        "function clearSelection",
        "function selectPart",
        "function selectSection",
        "function selectAssembly",
        "function selectBoundary",
        "function selectLoad",
        "function selectMesh",
        "function selectResult",
        "selectBoundary()",
        "selectLoad()",
        "selectMesh()",
        "selectPart()",
        "选择：",
        "当前选择",
        "对象名称",
        "对象说明",
        "TreeItem",
        "handleViewportSelection",
        "MouseArea",
        "onClicked",
        "onPressed",
        "onPositionChanged",
        "onReleased",
        "viewportScale",
        "viewportOffsetX",
        "viewportOffsetY",
        "showMesh",
        "showBoundary",
        "showLoad",
        "showResultOverlay",
    ]

    for snippet in expected_snippets:
        assert snippet in qml

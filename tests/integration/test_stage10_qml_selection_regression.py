from pathlib import Path


def test_stage10_qml_selection_regression():
    qml = Path("ui/qml/MainWorkbench.qml").read_text(encoding="utf-8")

    required_snippets = [
        "selectedGeometryType",
        "selectedGeometryId",
        "selectedFaceId",
        "function clearViewportSelection",
        "function handleViewportSelection",
        "function handleModelingClick",
        "function handleTargetSelectionClick",
        "function handleResultQueryClick",
        "function screenToModel",
        "viewportScale",
        "viewportOffsetX",
        "viewportOffsetY",
        "resultOverlayMode",
        "hasQueryMarker",
        "function drawMeshLayer",
        "function drawBoundaryLayer",
        "function drawLoadLayer",
        "function drawResultLayer",
    ]

    for snippet in required_snippets:
        assert snippet in qml

    forbidden_snippets = [
        "function selectPart",
        "function selectSection",
        "function selectAssembly",
        "function selectBoundary",
        "function selectLoad",
        "function selectMesh",
        "function selectResult",
        "lastPlateX",
        "lastPlateY",
        "lastPlateW",
        "lastPlateH",
    ]
    for snippet in forbidden_snippets:
        assert snippet not in qml

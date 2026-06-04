from __future__ import annotations

from ui.backend.workbench_bridge import WorkbenchBridge


def test_stage14_engineering_workflow(tmp_path):
    bridge = WorkbenchBridge()

    assert bridge.newProject()
    assert bridge.partCount == 0
    assert bridge.instanceCount == 0
    assert bridge.enterPartEditMode()
    assert bridge.createEmptySketchForActivePart()
    assert bridge.partCount == 1
    assert bridge.instanceCount == 0

    for point in ((0.0, 0.0), (2.0, 0.0), (2.0, 1.0), (0.0, 1.0)):
        assert bridge.addSketchPointFromViewport(*point)
    assert bridge.sketchPointCount == 4

    assert bridge.selectSketchPoint("p1")
    assert bridge.startEdgeFromSelectedPoint()
    assert bridge.connectEdgeToPoint("p2")
    assert bridge.selectSketchPoint("p2")
    assert bridge.startEdgeFromSelectedPoint()
    assert bridge.connectEdgeToPoint("p3")
    assert bridge.selectSketchPoint("p3")
    assert bridge.startEdgeFromSelectedPoint()
    assert bridge.connectEdgeToPoint("p4")
    assert bridge.selectSketchPoint("p4")
    assert bridge.startEdgeFromSelectedPoint()
    assert bridge.connectEdgeToPoint("p1")
    assert bridge.sketchEdgeCount == 4

    assert bridge.buildSketchFace()

    assert bridge.addMaterial("steel", 210e9, 0.3, "#8FB7D8")
    steel_id = next(option.split("|")[0].strip() for option in bridge.materialOptions if "steel" in option)
    assert bridge.assignMaterialToActivePart(steel_id, 0.01)

    assert bridge.generateQualityMeshForActivePart(0.25, 0.0, 25.0)
    assert bridge.sketchMeshNodeCount > 4
    assert bridge.sketchMeshElementCount > 2
    assert bridge.meshDegenerateElementCount == 0
    assert bridge.meshQualitySummaryText != ""

    assert bridge.selectGeometryEdge("e4")
    assert bridge.addFixedConstraintToSelectedTarget(True, True)
    assert bridge.selectGeometryEdge("e2")
    assert bridge.addLoadToSelectedTarget("edge_uniform", 0.0, -1000.0)

    assert bridge.solveCurrentModel()
    assert bridge.hasSolution is True
    assert bridge.nodeCount > 4
    assert bridge.elementCount > 2

    export_dir = tmp_path / "exports"
    assert bridge.exportResults(str(export_dir))
    assert (export_dir / "node_displacements.csv").exists()
    assert (export_dir / "element_results.csv").exists()
    assert (export_dir / "summary.txt").exists()

    file_path = tmp_path / "stage14_project.f2dw.json"
    assert bridge.saveCurrentProject(str(file_path))

    restored = WorkbenchBridge()
    assert restored.loadProject(str(file_path))
    assert restored.generateQualityMeshForActivePart(0.25, 0.0, 25.0)
    assert restored.selectGeometryEdge("e4")
    assert restored.addFixedConstraintToSelectedTarget(True, True)
    assert restored.selectGeometryEdge("e2")
    assert restored.addLoadToSelectedTarget("edge_uniform", 0.0, -1000.0)
    assert restored.solveCurrentModel()
    assert restored.hasSolution is True

import pytest

from ui.backend.workbench_bridge import WorkbenchBridge


def test_stage11_project_parameter_workflow(tmp_path):
    bridge = WorkbenchBridge()

    assert bridge.newProject() is True
    assert bridge.updateCurrentProjectParameters(
        3.0,
        1.5,
        200e9,
        0.28,
        0.02,
        -2000.0,
        5,
        3,
    ) is True

    project_path = tmp_path / "edited_project.f2dw.json"
    assert bridge.saveCurrentProject(str(project_path)) is True

    bridge2 = WorkbenchBridge()
    assert bridge2.loadProject(str(project_path)) is True
    assert bridge2.projectWidth == pytest.approx(3.0)
    assert bridge2.projectHeight == pytest.approx(1.5)
    assert bridge2.projectMeshNx == 5
    assert bridge2.projectMeshNy == 3

    assert bridge2.solveCurrentProject(bridge2.projectMeshNx, bridge2.projectMeshNy) is True
    assert bridge2.nodeCount == 24
    assert bridge2.elementCount == 30

    export_dir = tmp_path / "exports"
    assert bridge2.exportResults(str(export_dir)) is True
    assert (export_dir / "node_displacements.csv").exists()
    assert (export_dir / "element_results.csv").exists()
    assert (export_dir / "summary.txt").exists()

import pytest

from ui.backend.workbench_bridge import WorkbenchBridge


def test_stage12_part_edit_workflow(tmp_path):
    bridge = WorkbenchBridge()

    assert bridge.newProject() is True
    assert bridge.updateCurrentProjectParameters(2.0, 1.0, 210e9, 0.3, 0.01, -1000.0, 4, 2) is True
    assert bridge.addRectanglePart("large_part", 3.0, 1.5) is True
    assert bridge.activePartName == "large_part"

    assert bridge.updateCurrentProjectParameters(
        3.5,
        1.6,
        200e9,
        0.28,
        0.02,
        -2000.0,
        5,
        3,
    ) is True

    project_path = tmp_path / "multi_part_project.f2dw.json"
    assert bridge.saveCurrentProject(str(project_path)) is True

    bridge2 = WorkbenchBridge()
    assert bridge2.loadProject(str(project_path)) is True
    assert bridge2.partCount == 2
    assert bridge2.activePartName == "large_part"
    assert bridge2.projectWidth == pytest.approx(3.5)
    assert bridge2.projectHeight == pytest.approx(1.6)
    assert bridge2.projectMeshNx == 5
    assert bridge2.projectMeshNy == 3

    assert bridge2.solveCurrentProject(bridge2.projectMeshNx, bridge2.projectMeshNy) is True
    assert bridge2.nodeCount == 24
    assert bridge2.elementCount == 30

    assert bridge2.setActivePart("part_rectangle") is True
    assert bridge2.projectWidth == pytest.approx(2.0)
    assert bridge2.projectHeight == pytest.approx(1.0)

    assert bridge2.solveCurrentProject(4, 2) is True
    assert bridge2.nodeCount == 15
    assert bridge2.elementCount == 16

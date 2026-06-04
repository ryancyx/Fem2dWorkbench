import pytest

from ui.backend.workbench_bridge import WorkbenchBridge


def test_stage12b_assembly_instance_workflow(tmp_path):
    bridge = WorkbenchBridge()

    assert bridge.newProject() is True
    assert bridge.updateCurrentProjectParameters(2.0, 1.0, 210e9, 0.3, 0.01, -1000.0, 4, 2) is True
    assert bridge.addInstanceForPart(bridge.activePartId, "base instance", 0.0, 0.0) is True
    assert bridge.addRectanglePart("large_part", 3.0, 1.5) is True
    assert bridge.addInstanceForPart(bridge.activePartId, "large instance", 0.0, 0.0) is True
    assert bridge.moveActiveInstance(2.0, 1.0) is True

    project_path = tmp_path / "assembly_project.f2dw.json"
    assert bridge.saveCurrentProject(str(project_path)) is True

    bridge2 = WorkbenchBridge()
    assert bridge2.loadProject(str(project_path)) is True

    assert bridge2.partCount == 2
    assert bridge2.instanceCount == 2
    assert bridge2.activeInstanceName
    assert bridge2.activeInstanceTx == pytest.approx(2.0)
    assert bridge2.activeInstanceTy == pytest.approx(1.0)
    assert bridge2.activeInstancePartId == bridge2.activePartId

    assert bridge2.solveCurrentProject(5, 3) is False
    assert "多实例" in bridge2.statusText or "装配联合求解" in bridge2.statusText

    assert bridge2.setActiveInstance("inst_1") is True
    assert bridge2.projectWidth == pytest.approx(2.0)
    assert bridge2.projectHeight == pytest.approx(1.0)

    assert bridge2.solveCurrentProject(4, 2) is False
    assert "多实例" in bridge2.statusText or "装配联合求解" in bridge2.statusText

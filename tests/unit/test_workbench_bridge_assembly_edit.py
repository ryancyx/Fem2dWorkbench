import pytest

from ui.backend.workbench_bridge import WorkbenchBridge


def _bootstrap_rectangle_project(bridge: WorkbenchBridge) -> None:
    assert bridge.updateCurrentProjectParameters(2.0, 1.0, 210e9, 0.3, 0.01, -1000.0, 4, 2) is True


def test_bridge_new_project_starts_without_instance():
    bridge = WorkbenchBridge()

    assert bridge.newProject() is True

    assert bridge.instanceCount == 0
    assert bridge.activeInstanceId == ""
    assert bridge.activeInstancePartId == ""


def test_bridge_add_rectangle_part_requires_explicit_instance():
    bridge = WorkbenchBridge()
    bridge.newProject()
    _bootstrap_rectangle_project(bridge)

    assert bridge.addRectanglePart("part2", 3.0, 1.5) is True

    assert bridge.partCount == 2
    assert bridge.instanceCount == 0
    assert bridge.activeInstancePartId == ""
    assert bridge.addInstanceForPart(bridge.activePartId, "part2 instance", 0.0, 0.0) is True
    assert bridge.instanceCount == 1
    assert bridge.activeInstancePartId == bridge.activePartId
    assert bridge.projectWidth == pytest.approx(3.0)


def test_bridge_set_active_instance_syncs_active_part_and_parameters():
    bridge = WorkbenchBridge()
    bridge.newProject()
    _bootstrap_rectangle_project(bridge)
    assert bridge.addInstanceForPart(bridge.activePartId, "base instance", 0.0, 0.0) is True
    bridge.addRectanglePart("part2", 3.0, 1.5)
    assert bridge.addInstanceForPart(bridge.activePartId, "part2 instance", 0.0, 0.0) is True

    assert bridge.setActiveInstance("inst_1") is True

    assert bridge.activePartId == "part_rectangle"
    assert bridge.projectWidth == pytest.approx(2.0)
    assert bridge.projectHeight == pytest.approx(1.0)


def test_bridge_move_active_instance_updates_transform():
    bridge = WorkbenchBridge()
    bridge.newProject()
    _bootstrap_rectangle_project(bridge)
    assert bridge.addInstanceForPart(bridge.activePartId, "base instance", 0.0, 0.0) is True

    assert bridge.moveActiveInstance(2.0, -1.0) is True

    assert bridge.activeInstanceTx == pytest.approx(2.0)
    assert bridge.activeInstanceTy == pytest.approx(-1.0)


def test_bridge_solve_uses_active_instance_part():
    bridge = WorkbenchBridge()
    bridge.newProject()
    _bootstrap_rectangle_project(bridge)
    bridge.addRectanglePart("part2", 3.0, 1.5)
    assert bridge.addInstanceForPart(bridge.activePartId, "part2 instance", 0.0, 0.0) is True
    bridge.updateCurrentProjectParameters(
        3.0,
        1.5,
        200e9,
        0.28,
        0.02,
        -2000.0,
        5,
        3,
    )

    assert bridge.solveCurrentProject(bridge.projectMeshNx, bridge.projectMeshNy) is True
    assert bridge.nodeCount == 24
    assert bridge.elementCount == 30


def test_bridge_delete_last_instance_leaves_empty_assembly():
    bridge = WorkbenchBridge()
    bridge.newProject()
    _bootstrap_rectangle_project(bridge)
    assert bridge.addInstanceForPart(bridge.activePartId, "base instance", 0.0, 0.0) is True

    assert bridge.deleteActiveInstance() is True
    assert bridge.instanceCount == 0
    assert bridge.activeInstanceId == ""

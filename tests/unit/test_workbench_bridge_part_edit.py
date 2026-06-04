import pytest

from ui.backend.workbench_bridge import WorkbenchBridge


def _bootstrap_rectangle_project(bridge: WorkbenchBridge) -> None:
    assert bridge.updateCurrentProjectParameters(2.0, 1.0, 210e9, 0.3, 0.01, -1000.0, 4, 2) is True


def test_bridge_new_project_starts_empty():
    bridge = WorkbenchBridge()

    assert bridge.newProject() is True

    assert bridge.partCount == 0
    assert bridge.activePartId == ""
    assert bridge.activePartName == ""
    assert len(bridge.partOptions) == 0


def test_bridge_add_rectangle_part_updates_active_part_and_parameters():
    bridge = WorkbenchBridge()
    bridge.newProject()
    _bootstrap_rectangle_project(bridge)

    assert bridge.addRectanglePart("part2", 3.0, 1.5) is True

    assert bridge.partCount == 2
    assert "part2" in bridge.activePartName
    assert bridge.projectWidth == pytest.approx(3.0)
    assert bridge.projectHeight == pytest.approx(1.5)


def test_bridge_set_active_part_syncs_parameters():
    bridge = WorkbenchBridge()
    bridge.newProject()
    _bootstrap_rectangle_project(bridge)
    bridge.addRectanglePart("part2", 3.0, 1.5)

    assert bridge.setActivePart("part_rectangle") is True

    assert bridge.projectWidth == pytest.approx(2.0)
    assert bridge.projectHeight == pytest.approx(1.0)


def test_bridge_update_parameters_apply_to_active_part_only():
    bridge = WorkbenchBridge()
    bridge.newProject()
    _bootstrap_rectangle_project(bridge)
    bridge.addRectanglePart("part2", 3.0, 1.5)
    second_part_id = bridge.activePartId

    assert bridge.updateCurrentProjectParameters(
        4.0,
        2.0,
        200e9,
        0.28,
        0.02,
        -2000.0,
        5,
        3,
    ) is True

    assert bridge.setActivePart("part_rectangle") is True
    assert bridge.projectWidth == pytest.approx(2.0)
    assert bridge.projectHeight == pytest.approx(1.0)

    assert bridge.setActivePart(second_part_id) is True
    assert bridge.projectWidth == pytest.approx(4.0)
    assert bridge.projectHeight == pytest.approx(2.0)


def test_bridge_solve_uses_active_part():
    bridge = WorkbenchBridge()
    bridge.newProject()
    _bootstrap_rectangle_project(bridge)
    bridge.addRectanglePart("part2", 3.0, 1.5)
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


def test_bridge_delete_last_part_fails():
    bridge = WorkbenchBridge()
    bridge.newProject()
    _bootstrap_rectangle_project(bridge)

    assert bridge.deleteActivePart() is False

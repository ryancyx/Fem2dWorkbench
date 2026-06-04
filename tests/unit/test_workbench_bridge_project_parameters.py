import pytest

from services.project_factory_service import create_rectangle_plate_project
from services.project_file_service import save_workbench_project
from ui.backend.workbench_bridge import WorkbenchBridge


def test_bridge_new_project_syncs_parameter_cache():
    bridge = WorkbenchBridge()

    assert bridge.newProject() is True

    assert bridge.projectWidth == pytest.approx(2.0)
    assert bridge.projectHeight == pytest.approx(1.0)
    assert bridge.projectYoungModulus == pytest.approx(210e9)
    assert bridge.projectPoissonRatio == pytest.approx(0.3)
    assert bridge.projectThickness == pytest.approx(0.01)
    assert bridge.projectEdgeQy == pytest.approx(-1000.0)
    assert bridge.projectMeshNx == 4
    assert bridge.projectMeshNy == 2


def test_bridge_update_current_project_parameters():
    bridge = WorkbenchBridge()
    bridge.newProject()

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

    assert bridge.projectWidth == pytest.approx(3.0)
    assert bridge.projectHeight == pytest.approx(1.5)
    assert bridge.projectYoungModulus == pytest.approx(200e9)
    assert bridge.projectPoissonRatio == pytest.approx(0.28)
    assert bridge.projectThickness == pytest.approx(0.02)
    assert bridge.projectEdgeQy == pytest.approx(-2000.0)
    assert bridge.projectMeshNx == 5
    assert bridge.projectMeshNy == 3
    assert bridge.projectDirty is True
    assert bridge.hasSolution is False


def test_bridge_load_project_syncs_parameters(tmp_path):
    project = create_rectangle_plate_project(
        width=3.0,
        height=1.5,
        young_modulus=200e9,
        poisson_ratio=0.28,
        thickness=0.02,
        qy=-2000.0,
        mesh_nx=5,
        mesh_ny=3,
    )
    file_path = save_workbench_project(project, tmp_path / "project.f2dw.json")
    bridge = WorkbenchBridge()

    assert bridge.loadProject(str(file_path)) is True

    assert bridge.projectWidth == pytest.approx(3.0)
    assert bridge.projectHeight == pytest.approx(1.5)
    assert bridge.projectYoungModulus == pytest.approx(200e9)
    assert bridge.projectEdgeQy == pytest.approx(-2000.0)
    assert bridge.projectMeshNx == 5
    assert bridge.projectMeshNy == 3


def test_bridge_solve_uses_updated_mesh_parameters():
    bridge = WorkbenchBridge()

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
    assert bridge.solveCurrentProject(bridge.projectMeshNx, bridge.projectMeshNy) is True

    assert bridge.nodeCount == (5 + 1) * (3 + 1)
    assert bridge.elementCount == 2 * 5 * 3


def test_bridge_update_invalid_project_parameters_fails():
    bridge = WorkbenchBridge()

    assert bridge.updateCurrentProjectParameters(
        0.0,
        1.5,
        200e9,
        0.28,
        0.02,
        -2000.0,
        5,
        3,
    ) is False
    assert "width" in bridge.statusText

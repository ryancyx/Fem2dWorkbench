from ui.backend.workbench_bridge import WorkbenchBridge
from services.project_factory_service import create_rectangle_plate_project
from services.project_file_service import save_workbench_project


def test_workbench_bridge_new_project():
    bridge = WorkbenchBridge()

    assert bridge.newProject() is True

    assert bridge.hasProject is True
    assert bridge.projectName
    assert bridge.projectDirty is True


def test_workbench_bridge_save_current_project(tmp_path):
    bridge = WorkbenchBridge()
    bridge.newProject()
    file_path = tmp_path / "project.f2dw.json"

    assert bridge.saveCurrentProject(str(file_path)) is True

    assert file_path.exists()
    assert bridge.projectPath
    assert bridge.projectDirty is False


def test_workbench_bridge_load_project(tmp_path):
    project = create_rectangle_plate_project(2.0, 1.0, 210e9, 0.3, 0.01, -1000.0)
    file_path = tmp_path / "project.f2dw.json"
    save_workbench_project(project, file_path)
    bridge = WorkbenchBridge()

    assert bridge.loadProject(str(file_path)) is True

    assert bridge.hasProject is True
    assert str(file_path) in bridge.projectPath
    assert bridge.projectDirty is False
    assert bridge.solveCurrentProject(4, 2) is True


def test_workbench_bridge_save_without_project_fails():
    bridge = WorkbenchBridge()

    assert bridge.saveCurrentProject("project.f2dw.json") is False
    assert "没有可保存的工程" in bridge.statusText


def test_workbench_bridge_load_missing_project_fails(tmp_path):
    bridge = WorkbenchBridge()
    missing_path = tmp_path / "missing.f2dw.json"

    assert bridge.loadProject(str(missing_path)) is False
    assert "打开工程失败" in bridge.statusText

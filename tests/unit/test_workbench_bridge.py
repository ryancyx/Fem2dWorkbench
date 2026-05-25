from ui.backend.workbench_bridge import WorkbenchBridge


def test_workbench_bridge_create_default_project():
    bridge = WorkbenchBridge()

    result = bridge.createDefaultProject(2.0, 1.0, 210e9, 0.3, 0.01, -1000.0)

    assert result is True
    assert bridge.current_project is not None
    assert "工程" in bridge.statusText or "创建" in bridge.statusText


def test_workbench_bridge_solve_current_project():
    bridge = WorkbenchBridge()
    bridge.createDefaultProject(2.0, 1.0, 210e9, 0.3, 0.01, -1000.0)

    result = bridge.solveCurrentProject(4, 2)

    assert result is True
    assert bridge.hasSolution is True
    assert bridge.nodeCount > 0
    assert bridge.elementCount > 0
    assert bridge.nodeRowsPreview
    assert bridge.elementRowsPreview


def test_workbench_bridge_export_results(tmp_path):
    bridge = WorkbenchBridge()
    bridge.createDefaultProject(2.0, 1.0, 210e9, 0.3, 0.01, -1000.0)
    bridge.solveCurrentProject(4, 2)

    result = bridge.exportResults(str(tmp_path))

    assert result is True
    assert (tmp_path / "node_displacements.csv").exists()
    assert (tmp_path / "element_results.csv").exists()
    assert (tmp_path / "summary.txt").exists()


def test_workbench_bridge_solve_without_project_fails():
    bridge = WorkbenchBridge()

    result = bridge.solveCurrentProject(4, 2)

    assert result is False
    assert "先创建工程" in bridge.statusText


def test_workbench_bridge_export_without_solution_fails(tmp_path):
    bridge = WorkbenchBridge()

    result = bridge.exportResults(str(tmp_path))

    assert result is False
    assert "没有" in bridge.statusText and "结果" in bridge.statusText

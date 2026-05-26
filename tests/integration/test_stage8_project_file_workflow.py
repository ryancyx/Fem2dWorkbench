from ui.backend.workbench_bridge import WorkbenchBridge


def test_stage8_project_file_workflow(tmp_path):
    file_path = tmp_path / "project.f2dw.json"
    export_dir = tmp_path / "exports"

    bridge = WorkbenchBridge()
    assert bridge.createDefaultProject(2.0, 1.0, 210e9, 0.3, 0.01, -1000.0) is True
    assert bridge.saveCurrentProject(str(file_path)) is True

    bridge2 = WorkbenchBridge()
    assert bridge2.loadProject(str(file_path)) is True
    assert bridge2.solveCurrentProject(4, 2) is True
    assert bridge2.exportResults(str(export_dir)) is True

    assert file_path.exists()
    assert bridge2.hasProject is True
    assert bridge2.hasSolution is True
    assert (export_dir / "node_displacements.csv").exists()
    assert (export_dir / "element_results.csv").exists()
    assert (export_dir / "summary.txt").exists()

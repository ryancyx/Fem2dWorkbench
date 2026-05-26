import pytest

from services.project_factory_service import create_rectangle_plate_project
from services.project_file_service import load_workbench_project, save_workbench_project


def test_save_and_load_workbench_project_roundtrip(tmp_path):
    project = create_rectangle_plate_project(2.0, 1.0, 210e9, 0.3, 0.01, -1000.0)
    file_path = tmp_path / "demo.f2dw.json"

    saved_path = save_workbench_project(project, file_path)
    restored = load_workbench_project(saved_path)

    assert saved_path == file_path
    assert restored.to_dict() == project.to_dict()


def test_load_missing_project_file_raises(tmp_path):
    missing_path = tmp_path / "missing.f2dw.json"

    with pytest.raises(FileNotFoundError, match="missing.f2dw.json"):
        load_workbench_project(missing_path)

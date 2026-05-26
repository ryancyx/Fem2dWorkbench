from __future__ import annotations

from pathlib import Path

from core.engineering.engineering_project import EngineeringProject
from core.io.project_json import load_project_from_json, save_project_to_json


def save_workbench_project(
    project: EngineeringProject,
    file_path: str | Path,
) -> Path:
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    save_project_to_json(project, path)
    return path


def load_workbench_project(file_path: str | Path) -> EngineeringProject:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Project file does not exist: {path}")

    project = load_project_from_json(path)
    project.validate_references()
    return project

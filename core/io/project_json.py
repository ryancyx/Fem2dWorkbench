from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.engineering.engineering_project import EngineeringProject


def save_project_to_json(project: EngineeringProject, file_path: str | Path) -> None:
    project.validate_references()
    path = Path(file_path)
    path.write_text(
        json.dumps(project.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def load_project_from_json(file_path: str | Path) -> EngineeringProject:
    path = Path(file_path)
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return EngineeringProject.from_dict(data)

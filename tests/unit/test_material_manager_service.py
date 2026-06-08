from __future__ import annotations

import pytest

from core.engineering.engineering_project import EngineeringProject
from services.material_manager_service import add_material, list_materials, update_material


def test_material_manager_service_add_material_saves_unit_weight() -> None:
    project = EngineeringProject(name="unit_weight_project")

    add_material(project, "steel", 210e9, 0.3, "#8FB7D8", 78500.0)

    rows = list_materials(project)
    assert len(rows) == 1
    assert rows[0]["unit_weight"] == pytest.approx(78500.0)


def test_material_manager_service_update_material_changes_unit_weight() -> None:
    project = EngineeringProject(name="unit_weight_project")
    add_material(project, "steel", 210e9, 0.3, "#8FB7D8", 78500.0)
    material_id = project.materials[0].id

    update_material(project, material_id, "steel", 210e9, 0.3, "#8FB7D8", 80000.0)

    rows = list_materials(project)
    assert rows[0]["unit_weight"] == pytest.approx(80000.0)

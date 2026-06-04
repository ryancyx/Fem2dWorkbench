from __future__ import annotations

import pytest

from services.material_manager_service import (
    add_material,
    assign_material_to_part,
    delete_material,
    get_part_material_info,
    list_materials,
    list_sections,
    update_material,
)
from services.project_factory_service import create_rectangle_plate_project


def test_add_update_delete_unused_material_and_validate_references():
    project = create_rectangle_plate_project(2.0, 1.0, 210e9, 0.3, 0.01, -1000.0)

    add_material(project, "aluminum", 70e9, 0.33, "#CCCCCC")
    materials = list_materials(project)
    assert len(materials) == 2
    mat_id = next(row["id"] for row in materials if row["name"] == "aluminum")

    update_material(project, mat_id, "aluminum_6061", 69e9, 0.32, "#BBBBBB")
    updated = next(row for row in list_materials(project) if row["id"] == mat_id)
    assert updated["name"] == "aluminum_6061"
    assert updated["young_modulus"] == 69e9

    delete_material(project, mat_id)
    assert all(row["id"] != mat_id for row in list_materials(project))
    project.validate_references()


def test_delete_referenced_material_is_rejected():
    project = create_rectangle_plate_project(2.0, 1.0, 210e9, 0.3, 0.01, -1000.0)

    with pytest.raises(ValueError, match="section"):
        delete_material(project, "mat_steel")


def test_assign_material_to_part_and_get_part_material_info():
    project = create_rectangle_plate_project(2.0, 1.0, 210e9, 0.3, 0.01, -1000.0)
    add_material(project, "aluminum", 70e9, 0.33, "#C0C0C0")
    material_id = next(row["id"] for row in list_materials(project) if row["name"] == "aluminum")

    assign_material_to_part(project, "part_rectangle", material_id, 0.02)
    info = get_part_material_info(project, "part_rectangle")

    assert info["material_id"] == material_id
    assert info["material_name"] == "aluminum"
    assert info["thickness"] == 0.02
    assert any(row["material_id"] == material_id for row in list_sections(project))
    project.validate_references()

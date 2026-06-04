import pytest

from services.part_edit_service import (
    add_rectangle_part,
    delete_part,
    get_active_part_id,
    list_parts,
    rename_part,
    set_active_part,
)
from services.project_factory_service import create_rectangle_plate_project
from services.project_parameter_service import extract_workbench_project_parameters


def test_list_parts_and_active_part_from_factory_project():
    project = create_rectangle_plate_project(
        width=2.0,
        height=1.0,
        young_modulus=210e9,
        poisson_ratio=0.3,
        thickness=0.01,
        qy=-1000.0,
    )

    parts = list_parts(project)

    assert len(parts) == 1
    assert parts[0]["id"] == "part_rectangle"
    assert parts[0]["is_active"] is True
    assert get_active_part_id(project) == "part_rectangle"


def test_add_rectangle_part_makes_it_active():
    project = create_rectangle_plate_project(
        width=2.0,
        height=1.0,
        young_modulus=210e9,
        poisson_ratio=0.3,
        thickness=0.01,
        qy=-1000.0,
    )

    add_rectangle_part(project, name="part2", width=3.0, height=1.5)

    parts = list_parts(project)
    assert len(parts) == 2
    assert get_active_part_id(project) == "part_rectangle_2"
    params = extract_workbench_project_parameters(project)
    assert params.width == pytest.approx(3.0)
    assert params.height == pytest.approx(1.5)


def test_set_active_part_switches_active_part():
    project = create_rectangle_plate_project(
        width=2.0,
        height=1.0,
        young_modulus=210e9,
        poisson_ratio=0.3,
        thickness=0.01,
        qy=-1000.0,
    )
    add_rectangle_part(project, name="part2", width=3.0, height=1.5)

    set_active_part(project, "part_rectangle")

    assert get_active_part_id(project) == "part_rectangle"


def test_rename_part_updates_name():
    project = create_rectangle_plate_project(
        width=2.0,
        height=1.0,
        young_modulus=210e9,
        poisson_ratio=0.3,
        thickness=0.01,
        qy=-1000.0,
    )

    rename_part(project, "part_rectangle", "renamed")

    assert list_parts(project)[0]["name"] == "renamed"


def test_delete_active_part_switches_to_remaining_part():
    project = create_rectangle_plate_project(
        width=2.0,
        height=1.0,
        young_modulus=210e9,
        poisson_ratio=0.3,
        thickness=0.01,
        qy=-1000.0,
    )
    add_rectangle_part(project, name="part2", width=3.0, height=1.5)

    delete_part(project, get_active_part_id(project))

    assert len(project.parts) == 1
    assert get_active_part_id(project) == "part_rectangle"


def test_delete_last_part_rejected():
    project = create_rectangle_plate_project(
        width=2.0,
        height=1.0,
        young_modulus=210e9,
        poisson_ratio=0.3,
        thickness=0.01,
        qy=-1000.0,
    )

    with pytest.raises(ValueError):
        delete_part(project, "part_rectangle")

from services.assembly_edit_service import (
    add_instance,
    delete_instance,
    ensure_default_instance,
    get_active_instance_id,
    list_instances,
    move_instance,
    rename_instance,
    set_active_instance,
)
from services.part_edit_service import add_rectangle_part, get_active_part_id
from services.project_factory_service import create_rectangle_plate_project


def _project():
    return create_rectangle_plate_project(
        width=2.0,
        height=1.0,
        young_modulus=210e9,
        poisson_ratio=0.3,
        thickness=0.01,
        qy=-1000.0,
    )


def test_ensure_default_instance_is_stage16_noop():
    project = _project()
    ensure_default_instance(project)

    assert list_instances(project) == []
    assert get_active_instance_id(project) == ""


def test_add_instance_for_existing_part():
    project = _project()
    add_instance(project, get_active_part_id(project), name="instance 1")
    add_rectangle_part(project, "part2", 3.0, 1.5)
    second_part_id = get_active_part_id(project)

    add_instance(project, second_part_id, name="instance 2")

    instances = list_instances(project)
    assert len(instances) == 2
    assert instances[-1]["is_active"] is True
    assert instances[-1]["part_id"] == second_part_id


def test_set_active_instance_syncs_active_part():
    project = _project()
    add_instance(project, get_active_part_id(project), name="instance 1")
    add_rectangle_part(project, "part2", 3.0, 1.5)
    second_part_id = get_active_part_id(project)
    add_instance(project, second_part_id, name="instance 2")

    set_active_instance(project, "inst_1")

    active = next(row for row in list_instances(project) if row["is_active"])
    assert get_active_part_id(project) == active["part_id"]


def test_move_instance_updates_tx_ty():
    project = _project()
    add_instance(project, get_active_part_id(project), name="instance 1")

    move_instance(project, "inst_1", 1.5, -2.0)

    instance = list_instances(project)[0]
    assert instance["tx"] == 1.5
    assert instance["ty"] == -2.0


def test_rename_instance_updates_name():
    project = _project()
    add_instance(project, get_active_part_id(project), name="instance 1")

    rename_instance(project, "inst_1", "renamed")

    assert list_instances(project)[0]["name"] == "renamed"


def test_delete_active_instance_switches_to_remaining():
    project = _project()
    add_instance(project, "part_rectangle", name="instance 1")
    add_instance(project, "part_rectangle", name="instance 2")

    delete_instance(project, get_active_instance_id(project))

    assert len(list_instances(project)) == 1
    assert get_active_instance_id(project) == "inst_1"


def test_delete_last_instance_leaves_empty_assembly():
    project = _project()
    add_instance(project, "part_rectangle", name="instance 1")

    delete_instance(project, "inst_1")

    assert list_instances(project) == []
    assert get_active_instance_id(project) == ""

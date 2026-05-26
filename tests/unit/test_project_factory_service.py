import pytest

from services.project_factory_service import create_rectangle_plate_project


def test_create_rectangle_plate_project_basic_structure():
    project = create_rectangle_plate_project(
        width=2.0,
        height=1.0,
        young_modulus=210e9,
        poisson_ratio=0.3,
        thickness=0.01,
        qy=-1000.0,
        project_name="rectangle_demo",
    )

    assert project.name == "rectangle_demo"
    assert len(project.materials) == 1
    assert len(project.sections) == 1
    assert len(project.parts) == 1
    assert len(project.analysis_steps) == 1
    assert len(project.boundary_conditions) == 1
    assert len(project.loads) == 1
    assert project.parts[0].id == "part_rectangle"
    project.validate_references()


def test_create_rectangle_plate_project_rejects_invalid_geometry():
    with pytest.raises(ValueError, match="width"):
        create_rectangle_plate_project(0.0, 1.0, 210e9, 0.3, 0.01, -1000.0)

    with pytest.raises(ValueError, match="height"):
        create_rectangle_plate_project(2.0, 0.0, 210e9, 0.3, 0.01, -1000.0)


def test_create_rectangle_plate_project_rejects_invalid_material():
    with pytest.raises(ValueError, match="young_modulus"):
        create_rectangle_plate_project(2.0, 1.0, 0.0, 0.3, 0.01, -1000.0)

    with pytest.raises(ValueError, match="poisson_ratio"):
        create_rectangle_plate_project(2.0, 1.0, 210e9, 0.6, 0.01, -1000.0)

    with pytest.raises(ValueError, match="thickness"):
        create_rectangle_plate_project(2.0, 1.0, 210e9, 0.3, 0.0, -1000.0)

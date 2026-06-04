import pytest

from services.project_factory_service import create_rectangle_plate_project
from services.project_parameter_service import (
    WorkbenchProjectParameters,
    apply_workbench_project_parameters,
    extract_workbench_project_parameters,
    parameters_from_dict,
    parameters_to_dict,
    validate_workbench_project_parameters,
)


def test_extract_workbench_project_parameters_from_factory_project():
    project = create_rectangle_plate_project(
        width=2.5,
        height=1.2,
        young_modulus=200e9,
        poisson_ratio=0.28,
        thickness=0.02,
        qy=-2000.0,
        mesh_nx=5,
        mesh_ny=3,
    )

    params = extract_workbench_project_parameters(project)

    assert params.width == pytest.approx(2.5)
    assert params.height == pytest.approx(1.2)
    assert params.young_modulus == pytest.approx(200e9)
    assert params.poisson_ratio == pytest.approx(0.28)
    assert params.thickness == pytest.approx(0.02)
    assert params.qy == pytest.approx(-2000.0)
    assert params.mesh_nx == 5
    assert params.mesh_ny == 3


def test_apply_workbench_project_parameters_updates_project():
    project = create_rectangle_plate_project(
        width=2.0,
        height=1.0,
        young_modulus=210e9,
        poisson_ratio=0.3,
        thickness=0.01,
        qy=-1000.0,
    )
    new_params = WorkbenchProjectParameters(
        width=3.0,
        height=1.5,
        young_modulus=200e9,
        poisson_ratio=0.28,
        thickness=0.02,
        qy=-2000.0,
        mesh_nx=5,
        mesh_ny=3,
    )

    apply_workbench_project_parameters(project, new_params)
    restored = extract_workbench_project_parameters(project)

    assert restored == new_params
    project.validate_references()


def test_invalid_parameters_are_rejected():
    base = dict(
        width=2.0,
        height=1.0,
        young_modulus=210e9,
        poisson_ratio=0.3,
        thickness=0.01,
        qy=-1000.0,
        mesh_nx=4,
        mesh_ny=2,
    )

    invalid_cases = [
        ("width", 0.0),
        ("height", 0.0),
        ("young_modulus", 0.0),
        ("thickness", 0.0),
        ("mesh_nx", 0),
        ("mesh_ny", 0),
    ]

    for field_name, value in invalid_cases:
        data = dict(base)
        data[field_name] = value
        with pytest.raises(ValueError, match=field_name):
            validate_workbench_project_parameters(WorkbenchProjectParameters(**data))


def test_parameters_dict_roundtrip():
    params = WorkbenchProjectParameters(
        width=3.0,
        height=1.5,
        young_modulus=200e9,
        poisson_ratio=0.28,
        thickness=0.02,
        qy=-2000.0,
        mesh_nx=5,
        mesh_ny=3,
    )

    restored = parameters_from_dict(parameters_to_dict(params))

    assert restored == params

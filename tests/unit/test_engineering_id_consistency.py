from core.engineering.analysis_step import AnalysisStep
from core.engineering.boundary_condition_definition import BoundaryConditionDefinition
from core.engineering.engineering_project import EngineeringProject
from core.engineering.geometry import GeometryModel
from core.engineering.load_definition import LoadDefinition
from core.engineering.material_definition import MaterialDefinition
from core.engineering.part import Part
from core.engineering.section import SectionDefinition
from core.io.project_json import load_project_from_json, save_project_to_json


def build_string_id_project() -> EngineeringProject:
    project = EngineeringProject(name="string_id_consistency_demo")

    project.add_material(
        MaterialDefinition(
            id="mat_steel",
            name="steel",
            young_modulus=210e9,
            poisson_ratio=0.3,
            color="#8FB7D8",
        )
    )

    project.add_section(
        SectionDefinition(
            id="sec_plate",
            name="steel_plate_section",
            material_id="mat_steel",
            thickness=0.01,
            plane_mode="stress",
        )
    )

    geometry = GeometryModel.create_rectangle(
        width=2.0,
        height=1.0,
        origin_x=0.0,
        origin_y=0.0,
    )

    project.add_part(
        Part(
            id="part_rectangle",
            name="rectangle_plate",
            geometry=geometry,
            section_id="sec_plate",
        )
    )

    project.add_analysis_step(
        AnalysisStep(
            id="step_static",
            name="static_step_1",
            step_type="static_linear",
        )
    )

    project.add_boundary_condition(
        BoundaryConditionDefinition(
            id="bc_fix_left",
            name="fix_left_edge",
            step_id="step_static",
            target_type="geometry_edge",
            target_id="left",
            ux_fixed=True,
            uy_fixed=True,
        )
    )

    project.add_load(
        LoadDefinition(
            id="load_right_down",
            name="right_edge_downward_uniform_load",
            step_id="step_static",
            target_type="geometry_edge",
            target_id="right",
            qx=0.0,
            qy=-1000.0,
            load_type="edge_uniform",
        )
    )

    project.validate_references()
    return project


def assert_engineering_ids_are_strings(project: EngineeringProject) -> None:
    """
    工程层与几何层统一使用字符串 ID。

    注意：
    MeshModel 和 FEMModel 不在这里检查。
    后续规则是：
    - EngineeringProject / GeometryModel: str id
    - MeshModel: int node/element id
    - FEMModel: int node/element/material/load/constraint id
    """
    for material in project.materials:
        assert isinstance(material.id, str)

    for section in project.sections:
        assert isinstance(section.id, str)
        assert isinstance(section.material_id, str)

    for part in project.parts:
        assert isinstance(part.id, str)

        if part.section_id is not None:
            assert isinstance(part.section_id, str)

        for point in part.geometry.points:
            assert isinstance(point.id, str)

        for edge in part.geometry.edges:
            assert isinstance(edge.id, str)
            assert isinstance(edge.start_point_id, str)
            assert isinstance(edge.end_point_id, str)

        for face in part.geometry.faces:
            assert isinstance(face.id, str)

            for edge_id in face.edge_ids:
                assert isinstance(edge_id, str)

    for step in project.analysis_steps:
        assert isinstance(step.id, str)

    for load in project.loads:
        assert isinstance(load.id, str)
        assert isinstance(load.step_id, str)
        assert isinstance(load.target_id, str)

    for bc in project.boundary_conditions:
        assert isinstance(bc.id, str)
        assert isinstance(bc.step_id, str)
        assert isinstance(bc.target_id, str)


def test_engineering_project_uses_string_ids_before_json_roundtrip():
    project = build_string_id_project()

    project.validate_references()
    assert_engineering_ids_are_strings(project)

    assert project.get_material_by_id("mat_steel") is not None
    assert project.get_section_by_id("sec_plate") is not None
    assert project.get_part_by_id("part_rectangle") is not None
    assert project.get_analysis_step_by_id("step_static") is not None
    assert project.get_load_by_id("load_right_down") is not None
    assert project.get_boundary_condition_by_id("bc_fix_left") is not None


def test_engineering_project_keeps_string_ids_after_dict_roundtrip():
    project = build_string_id_project()

    restored = EngineeringProject.from_dict(project.to_dict())

    restored.validate_references()
    assert restored.to_dict() == project.to_dict()
    assert_engineering_ids_are_strings(restored)

    assert restored.get_material_by_id("mat_steel") is not None
    assert restored.get_section_by_id("sec_plate") is not None
    assert restored.get_part_by_id("part_rectangle") is not None
    assert restored.get_analysis_step_by_id("step_static") is not None
    assert restored.get_load_by_id("load_right_down") is not None
    assert restored.get_boundary_condition_by_id("bc_fix_left") is not None


def test_engineering_project_keeps_string_ids_after_json_roundtrip(tmp_path):
    project = build_string_id_project()
    file_path = tmp_path / "string_id_consistency_demo.f2dw.json"

    save_project_to_json(project, file_path)
    restored = load_project_from_json(file_path)

    restored.validate_references()
    assert restored.to_dict() == project.to_dict()
    assert_engineering_ids_are_strings(restored)

    assert restored.get_material_by_id("mat_steel") is not None
    assert restored.get_section_by_id("sec_plate") is not None
    assert restored.get_part_by_id("part_rectangle") is not None
    assert restored.get_analysis_step_by_id("step_static") is not None
    assert restored.get_load_by_id("load_right_down") is not None
    assert restored.get_boundary_condition_by_id("bc_fix_left") is not None


def test_engineering_project_rejects_missing_string_reference():
    project = build_string_id_project()

    broken_part = project.get_part_by_id("part_rectangle")
    assert broken_part is not None

    broken_part.section_id = "missing_section"

    try:
        project.validate_references()
    except ValueError as exc:
        assert "missing_section" in str(exc)
    else:
        raise AssertionError("validate_references() should reject missing section id")
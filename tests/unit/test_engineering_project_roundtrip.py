from core.engineering.analysis_step import AnalysisStep
from core.engineering.assembly import PartInstance
from core.engineering.boundary_condition_definition import BoundaryConditionDefinition
from core.engineering.engineering_project import EngineeringProject
from core.engineering.geometry import GeometryModel
from core.engineering.load_definition import LoadDefinition
from core.engineering.material_definition import MaterialDefinition
from core.engineering.part import Part
from core.engineering.section import SectionDefinition
from core.io.project_json import load_project_from_json, save_project_to_json


def build_reference_engineering_project() -> EngineeringProject:
    project = EngineeringProject(
        name="rectangle_plate_demo",
        metadata={"description": "Reference engineering project for roundtrip tests"},
    )

    project.add_material(
        MaterialDefinition(
            id="steel",
            name="steel",
            young_modulus=210e9,
            poisson_ratio=0.3,
        )
    )
    project.add_section(
        SectionDefinition(
            id="plate_section",
            name="Plate section",
            material_id="steel",
            thickness=0.01,
            plane_mode="stress",
        )
    )
    project.add_part(
        Part(
            id="plate",
            name="Rectangle plate",
            geometry=GeometryModel.create_rectangle(width=2.0, height=1.0),
            section_id="plate_section",
        )
    )
    project.assembly.instances.append(
        PartInstance(
            id="plate_instance",
            name="Plate instance",
            part_id="plate",
        )
    )
    project.add_analysis_step(
        AnalysisStep(
            id="static_step",
            name="Static linear step",
            step_type="static_linear",
        )
    )
    project.add_boundary_condition(
        BoundaryConditionDefinition(
            id="fix_left",
            name="Fix left edge",
            step_id="static_step",
            target_type="geometry_edge",
            target_id="left",
            ux_fixed=True,
            uy_fixed=True,
        )
    )
    project.add_load(
        LoadDefinition(
            id="right_down",
            name="Right edge downward uniform load",
            step_id="static_step",
            target_type="geometry_edge",
            target_id="right",
            load_type="edge_uniform",
            qy=-1000.0,
        )
    )

    project.validate_references()
    return project


def test_engineering_project_dict_roundtrip():
    project = build_reference_engineering_project()

    restored = EngineeringProject.from_dict(project.to_dict())

    assert restored.to_dict() == project.to_dict()


def test_engineering_project_json_roundtrip(tmp_path):
    project = build_reference_engineering_project()
    file_path = tmp_path / "rectangle_plate_demo.json"

    save_project_to_json(project, file_path)
    restored = load_project_from_json(file_path)

    assert restored.to_dict() == project.to_dict()


def test_rectangle_geometry_basic_structure():
    geometry = GeometryModel.create_rectangle(width=2.0, height=1.0)

    assert len(geometry.points) == 4
    assert len(geometry.edges) == 4
    assert len(geometry.faces) == 1
    assert {edge.id for edge in geometry.edges} == {"left", "right", "top", "bottom"}

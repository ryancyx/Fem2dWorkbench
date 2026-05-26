from __future__ import annotations

from core.engineering.analysis_step import AnalysisStep
from core.engineering.boundary_condition_definition import BoundaryConditionDefinition
from core.engineering.engineering_project import EngineeringProject
from core.engineering.geometry import GeometryModel
from core.engineering.load_definition import LoadDefinition
from core.engineering.material_definition import MaterialDefinition
from core.engineering.part import Part
from core.engineering.section import SectionDefinition


def create_rectangle_plate_project(
    width: float,
    height: float,
    young_modulus: float,
    poisson_ratio: float,
    thickness: float,
    qy: float,
    project_name: str = "ui_rectangle_demo",
) -> EngineeringProject:
    _validate_positive("width", width)
    _validate_positive("height", height)
    _validate_positive("young_modulus", young_modulus)
    if not (-1.0 <= poisson_ratio <= 0.5):
        raise ValueError("poisson_ratio must be between -1.0 and 0.5")
    _validate_positive("thickness", thickness)

    project = EngineeringProject(name=project_name)
    geometry = GeometryModel.create_rectangle(width=width, height=height)

    project.add_material(
        MaterialDefinition(
            id="mat_steel",
            name="steel",
            young_modulus=young_modulus,
            poisson_ratio=poisson_ratio,
            color="#8FB7D8",
        )
    )
    project.add_section(
        SectionDefinition(
            id="sec_plate",
            name="steel_plate_section",
            material_id="mat_steel",
            thickness=thickness,
            plane_mode="stress",
        )
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
            name="static_step",
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
            load_type="edge_uniform",
            qx=0.0,
            qy=qy,
        )
    )
    project.validate_references()
    return project


def _validate_positive(field_name: str, value: float) -> None:
    if value <= 0.0:
        raise ValueError(f"{field_name} must be positive")

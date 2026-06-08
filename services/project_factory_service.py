from __future__ import annotations

from core.engineering.analysis_step import AnalysisStep
from core.engineering.boundary_condition_definition import BoundaryConditionDefinition
from core.engineering.engineering_project import EngineeringProject
from core.engineering.geometry import GeometryModel
from core.engineering.load_definition import LoadDefinition
from core.engineering.material_definition import MaterialDefinition
from core.engineering.part import Part
from core.engineering.section import SectionDefinition
from services.project_parameter_service import (
    WorkbenchProjectParameters,
    validate_workbench_project_parameters,
)


def create_empty_workbench_project(
    project_name: str = "untitled_project",
) -> EngineeringProject:
    project = EngineeringProject(name=project_name)
    project.metadata["mesh_nx"] = 4
    project.metadata["mesh_ny"] = 2
    project.metadata["active_part_id"] = ""
    project.metadata["active_instance_id"] = ""
    project.metadata["gravity_enabled"] = False
    project.metadata["gravity_direction_x"] = 0.0
    project.metadata["gravity_direction_y"] = -1.0
    project.add_material(
        MaterialDefinition(
            id="mat_steel",
            name="steel",
            young_modulus=210e9,
            poisson_ratio=0.3,
            color="#8FB7D8",
            unit_weight=78500.0,
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
    project.add_analysis_step(
        AnalysisStep(
            id="step_static",
            name="static_step",
            step_type="static_linear",
        )
    )
    project.validate_references()
    return project


def create_rectangle_plate_project(
    width: float,
    height: float,
    young_modulus: float,
    poisson_ratio: float,
    thickness: float,
    qy: float,
    project_name: str = "ui_rectangle_demo",
    mesh_nx: int = 4,
    mesh_ny: int = 2,
) -> EngineeringProject:
    validate_workbench_project_parameters(
        WorkbenchProjectParameters(
            width=width,
            height=height,
            young_modulus=young_modulus,
            poisson_ratio=poisson_ratio,
            thickness=thickness,
            qy=qy,
            mesh_nx=mesh_nx,
            mesh_ny=mesh_ny,
        )
    )

    project = EngineeringProject(name=project_name)
    project.metadata["mesh_nx"] = mesh_nx
    project.metadata["mesh_ny"] = mesh_ny
    project.metadata["active_part_id"] = "part_rectangle"
    project.metadata["gravity_enabled"] = False
    project.metadata["gravity_direction_x"] = 0.0
    project.metadata["gravity_direction_y"] = -1.0
    geometry = GeometryModel.create_rectangle(width=width, height=height)

    project.add_material(
        MaterialDefinition(
            id="mat_steel",
            name="steel",
            young_modulus=young_modulus,
            poisson_ratio=poisson_ratio,
            color="#8FB7D8",
            unit_weight=78500.0,
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

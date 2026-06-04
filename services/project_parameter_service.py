from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from core.engineering.boundary_condition_definition import BoundaryConditionDefinition
from core.engineering.engineering_project import EngineeringProject
from core.engineering.geometry import GeometryModel
from core.engineering.load_definition import LoadDefinition
from core.engineering.material_definition import MaterialDefinition
from core.engineering.part import Part
from core.engineering.section import SectionDefinition
from services.part_edit_service import get_active_part_id


@dataclass(slots=True)
class WorkbenchProjectParameters:
    width: float
    height: float
    young_modulus: float
    poisson_ratio: float
    thickness: float
    qy: float
    mesh_nx: int = 4
    mesh_ny: int = 2


def validate_workbench_project_parameters(params: WorkbenchProjectParameters) -> None:
    _validate_positive("width", params.width)
    _validate_positive("height", params.height)
    _validate_positive("young_modulus", params.young_modulus)
    if not (-1.0 <= params.poisson_ratio <= 0.5):
        raise ValueError("poisson_ratio must be between -1.0 and 0.5")
    _validate_positive("thickness", params.thickness)
    if params.mesh_nx < 1:
        raise ValueError("mesh_nx must be at least 1")
    if params.mesh_ny < 1:
        raise ValueError("mesh_ny must be at least 1")


def extract_workbench_project_parameters(
    project: EngineeringProject,
    part_id: str | None = None,
) -> WorkbenchProjectParameters:
    part = _target_part(project, part_id)
    section = _section_for_part(project, part)
    material = _material_for_section(project, section)
    width, height = _rectangle_size_from_geometry(part.geometry)
    load = _preferred_load(project)
    qy = float(project.metadata.get("default_qy", -1000.0)) if load is None else load.qy

    params = WorkbenchProjectParameters(
        width=width,
        height=height,
        young_modulus=material.young_modulus,
        poisson_ratio=material.poisson_ratio,
        thickness=section.thickness,
        qy=qy,
        mesh_nx=int(project.metadata.get("mesh_nx", 4)),
        mesh_ny=int(project.metadata.get("mesh_ny", 2)),
    )
    validate_workbench_project_parameters(params)
    return params


def apply_workbench_project_parameters(
    project: EngineeringProject,
    params: WorkbenchProjectParameters,
    part_id: str | None = None,
) -> EngineeringProject:
    validate_workbench_project_parameters(params)

    part = _target_part(project, part_id)
    section = _section_for_part(project, part)
    material = _material_for_section(project, section)

    part.geometry = GeometryModel.create_rectangle(width=params.width, height=params.height)
    material.young_modulus = params.young_modulus
    material.poisson_ratio = params.poisson_ratio
    section.thickness = params.thickness
    load = _ensure_preferred_load(project, params.qy)
    load.qy = params.qy
    _ensure_preferred_boundary_condition(project)
    project.metadata["mesh_nx"] = params.mesh_nx
    project.metadata["mesh_ny"] = params.mesh_ny
    project.metadata["default_qy"] = params.qy
    project.validate_references()
    return project


def parameters_to_dict(params: WorkbenchProjectParameters) -> dict[str, Any]:
    return asdict(params)


def parameters_from_dict(data: dict[str, Any]) -> WorkbenchProjectParameters:
    params = WorkbenchProjectParameters(
        width=float(data["width"]),
        height=float(data["height"]),
        young_modulus=float(data["young_modulus"]),
        poisson_ratio=float(data["poisson_ratio"]),
        thickness=float(data["thickness"]),
        qy=float(data["qy"]),
        mesh_nx=int(data.get("mesh_nx", 4)),
        mesh_ny=int(data.get("mesh_ny", 2)),
    )
    validate_workbench_project_parameters(params)
    return params


def _validate_positive(field_name: str, value: float) -> None:
    if value <= 0.0:
        raise ValueError(f"{field_name} must be positive")


def _target_part(project: EngineeringProject, part_id: str | None) -> Part:
    if part_id is None:
        part_id = get_active_part_id(project)
    part = project.get_part_by_id(part_id)
    if part is None:
        raise ValueError(f"Unknown part id: {part_id}")
    return part


def _preferred_part(project: EngineeringProject) -> Part:
    if not project.parts:
        raise ValueError("Project is missing parts")
    return project.get_part_by_id("part_rectangle") or project.parts[0]


def _preferred_material(project: EngineeringProject) -> MaterialDefinition:
    if not project.materials:
        raise ValueError("Project is missing materials")
    return project.get_material_by_id("mat_steel") or project.materials[0]


def _preferred_section(project: EngineeringProject) -> SectionDefinition:
    if not project.sections:
        raise ValueError("Project is missing sections")
    return project.get_section_by_id("sec_plate") or project.sections[0]


def _section_for_part(project: EngineeringProject, part: Part) -> SectionDefinition:
    if part.section_id is None:
        return _preferred_section(project)
    section = project.get_section_by_id(part.section_id)
    if section is None:
        raise ValueError(f"Part {part.id!r} references unknown section {part.section_id!r}")
    return section


def _material_for_section(
    project: EngineeringProject,
    section: SectionDefinition,
) -> MaterialDefinition:
    material = project.get_material_by_id(section.material_id)
    if material is None:
        raise ValueError(
            f"Section {section.id!r} references unknown material {section.material_id!r}"
        )
    return material


def _preferred_load(project: EngineeringProject) -> LoadDefinition | None:
    if not project.loads:
        return None

    preferred = project.get_load_by_id("load_right_down")
    if preferred is not None:
        return preferred

    for load in project.loads:
        if load.target_id == "right":
            return load
    return project.loads[0]


def _ensure_preferred_load(project: EngineeringProject, qy: float) -> LoadDefinition:
    load = _preferred_load(project)
    if load is not None:
        return load
    step_id = _preferred_step_id(project)
    load = LoadDefinition(
        id="load_right_down",
        name="right_edge_downward_uniform_load",
        step_id=step_id,
        target_type="geometry_edge",
        target_id="right",
        load_type="edge_uniform",
        qx=0.0,
        qy=qy,
    )
    project.add_load(load)
    return load


def _ensure_preferred_boundary_condition(project: EngineeringProject) -> BoundaryConditionDefinition:
    existing = project.get_boundary_condition_by_id("bc_fix_left")
    if existing is not None:
        return existing
    step_id = _preferred_step_id(project)
    boundary_condition = BoundaryConditionDefinition(
        id="bc_fix_left",
        name="fix_left_edge",
        step_id=step_id,
        target_type="geometry_edge",
        target_id="left",
        ux_fixed=True,
        uy_fixed=True,
    )
    project.add_boundary_condition(boundary_condition)
    return boundary_condition


def _preferred_step_id(project: EngineeringProject) -> str:
    step = project.get_analysis_step_by_id("step_static")
    if step is not None:
        return step.id
    if project.analysis_steps:
        return project.analysis_steps[0].id
    raise ValueError("Project is missing analysis steps")


def _rectangle_size_from_geometry(geometry: GeometryModel) -> tuple[float, float]:
    if not geometry.points:
        raise ValueError("Geometry is missing points")
    xs = [point.x for point in geometry.points]
    ys = [point.y for point in geometry.points]
    width = max(xs) - min(xs)
    height = max(ys) - min(ys)
    if width <= 0.0:
        raise ValueError("width must be positive")
    if height <= 0.0:
        raise ValueError("height must be positive")
    return width, height

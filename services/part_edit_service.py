from __future__ import annotations

from core.engineering.engineering_project import EngineeringProject
from core.engineering.geometry import GeometryModel
from core.engineering.part import Part


def get_active_part_id(project: EngineeringProject) -> str:
    active_part_id = str(project.metadata.get("active_part_id", ""))
    if active_part_id and project.get_part_by_id(active_part_id) is not None:
        return active_part_id
    if not project.parts:
        raise ValueError("Project has no parts")
    active_part_id = project.parts[0].id
    project.metadata["active_part_id"] = active_part_id
    return active_part_id


def set_active_part(project: EngineeringProject, part_id: str) -> EngineeringProject:
    if project.get_part_by_id(part_id) is None:
        raise ValueError(f"Unknown part id: {part_id}")
    project.metadata["active_part_id"] = part_id
    return project


def list_parts(project: EngineeringProject) -> list[dict]:
    if not project.parts:
        return []
    active_part_id = get_active_part_id(project)
    return [
        {
            "id": part.id,
            "name": part.name,
            "is_active": part.id == active_part_id,
        }
        for part in project.parts
    ]


def create_unique_part_id(project: EngineeringProject, base_id: str = "part_rectangle") -> str:
    existing_ids = {part.id for part in project.parts}
    if base_id not in existing_ids:
        return base_id
    index = 2
    while True:
        candidate = f"{base_id}_{index}"
        if candidate not in existing_ids:
            return candidate
        index += 1


def add_rectangle_part(
    project: EngineeringProject,
    name: str,
    width: float,
    height: float,
    section_id: str | None = None,
    make_active: bool = True,
) -> EngineeringProject:
    if width <= 0.0:
        raise ValueError("width must be positive")
    if height <= 0.0:
        raise ValueError("height must be positive")
    part_name = name.strip() if name else ""
    if not part_name:
        part_name = "rectangle_plate"
    resolved_section_id = section_id or _default_section_id(project)
    if project.get_section_by_id(resolved_section_id) is None:
        raise ValueError(f"Unknown section id: {resolved_section_id}")
    part = Part(
        id=create_unique_part_id(project),
        name=part_name,
        geometry=GeometryModel.create_rectangle(width=width, height=height),
        section_id=resolved_section_id,
    )
    project.parts.append(part)
    if make_active:
        project.metadata["active_part_id"] = part.id
    project.validate_references()
    return project


def add_sketch_part(
    project: EngineeringProject,
    name: str,
    section_id: str | None = None,
    make_active: bool = True,
) -> EngineeringProject:
    part_name = name.strip() if name else ""
    if not part_name:
        part_name = "sketch_part"
    resolved_section_id = section_id or _default_section_id(project)
    if project.get_section_by_id(resolved_section_id) is None:
        raise ValueError(f"Unknown section id: {resolved_section_id}")
    part = Part(
        id=create_unique_part_id(project, base_id="part_sketch"),
        name=part_name,
        geometry=GeometryModel(points=[], edges=[], faces=[]),
        section_id=resolved_section_id,
    )
    project.parts.append(part)
    if make_active:
        project.metadata["active_part_id"] = part.id
    project.validate_references()
    return project


def rename_part(project: EngineeringProject, part_id: str, new_name: str) -> EngineeringProject:
    part = project.get_part_by_id(part_id)
    if part is None:
        raise ValueError(f"Unknown part id: {part_id}")
    name = new_name.strip() if new_name else ""
    if not name:
        raise ValueError("new_name must not be empty")
    part.name = name
    return project


def delete_part(project: EngineeringProject, part_id: str) -> EngineeringProject:
    part = project.get_part_by_id(part_id)
    if part is None:
        raise ValueError(f"Unknown part id: {part_id}")
    if len(project.parts) <= 1:
        raise ValueError("Cannot delete the last part")
    project.parts = [existing for existing in project.parts if existing.id != part_id]
    project.assembly.instances = [
        instance for instance in project.assembly.instances if instance.part_id != part_id
    ]
    if project.metadata.get("active_part_id") == part_id:
        project.metadata["active_part_id"] = project.parts[0].id
    if project.metadata.get("active_instance_id") not in {instance.id for instance in project.assembly.instances}:
        project.metadata["active_instance_id"] = ""
    project.validate_references()
    return project


def _default_section_id(project: EngineeringProject) -> str:
    if project.get_section_by_id("sec_plate") is not None:
        return "sec_plate"
    if project.sections:
        return project.sections[0].id
    raise ValueError("Project has no sections")

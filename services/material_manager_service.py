from __future__ import annotations

from core.engineering.engineering_project import EngineeringProject
from core.engineering.material_definition import MaterialDefinition
from core.engineering.section import SectionDefinition


def list_materials(project: EngineeringProject) -> list[dict]:
    return [
        {
            "id": material.id,
            "name": material.name,
            "young_modulus": material.young_modulus,
            "poisson_ratio": material.poisson_ratio,
            "color": material.color,
            "unit_weight": material.unit_weight,
        }
        for material in project.materials
    ]


def list_sections(project: EngineeringProject) -> list[dict]:
    return [
        {
            "id": section.id,
            "name": section.name,
            "material_id": section.material_id,
            "thickness": section.thickness,
            "plane_mode": section.plane_mode,
        }
        for section in project.sections
    ]


def create_unique_material_id(project: EngineeringProject, base_id: str = "mat") -> str:
    return _create_unique_id({material.id for material in project.materials}, base_id)


def create_unique_section_id(project: EngineeringProject, base_id: str = "sec") -> str:
    return _create_unique_id({section.id for section in project.sections}, base_id)


def add_material(
    project: EngineeringProject,
    name: str,
    young_modulus: float,
    poisson_ratio: float,
    color: str,
    unit_weight: float = 0.0,
) -> EngineeringProject:
    material = MaterialDefinition(
        id=create_unique_material_id(project),
        name=(name or "").strip() or "material",
        young_modulus=float(young_modulus),
        poisson_ratio=float(poisson_ratio),
        color=(color or "").strip() or "#808080",
        unit_weight=float(unit_weight),
    )
    project.add_material(material)
    project.validate_references()
    return project


def update_material(
    project: EngineeringProject,
    material_id: str,
    name: str,
    young_modulus: float,
    poisson_ratio: float,
    color: str,
    unit_weight: float = 0.0,
) -> EngineeringProject:
    material = project.get_material_by_id(material_id)
    if material is None:
        raise ValueError(f"Unknown material id: {material_id}")
    material.name = (name or "").strip() or material.name
    material.young_modulus = float(young_modulus)
    material.poisson_ratio = float(poisson_ratio)
    material.color = (color or "").strip() or material.color
    material.unit_weight = float(unit_weight)
    material.__post_init__()
    project.validate_references()
    return project


def delete_material(project: EngineeringProject, material_id: str) -> EngineeringProject:
    material = project.get_material_by_id(material_id)
    if material is None:
        raise ValueError(f"Unknown material id: {material_id}")
    if any(section.material_id == material_id for section in project.sections):
        raise ValueError(f"Material {material_id!r} is referenced by a section")
    project.materials = [existing for existing in project.materials if existing.id != material_id]
    project.validate_references()
    return project


def add_or_update_section(
    project: EngineeringProject,
    name: str,
    material_id: str,
    thickness: float,
    plane_mode: str = "stress",
) -> str:
    if project.get_material_by_id(material_id) is None:
        raise ValueError(f"Unknown material id: {material_id}")
    section_name = (name or "").strip() or "section"
    thickness = float(thickness)

    for section in project.sections:
        if (
            section.material_id == material_id
            and section.thickness == thickness
            and section.plane_mode == plane_mode
        ):
            section.name = section_name
            project.validate_references()
            return section.id

    section = SectionDefinition(
        id=create_unique_section_id(project),
        name=section_name,
        material_id=material_id,
        thickness=thickness,
        plane_mode=plane_mode,
    )
    project.add_section(section)
    project.validate_references()
    return section.id


def assign_material_to_part(
    project: EngineeringProject,
    part_id: str,
    material_id: str,
    thickness: float,
) -> EngineeringProject:
    from services.face_material_service import assign_material_to_part as assign_to_part_faces

    return assign_to_part_faces(project, part_id, material_id, thickness)


def get_part_material_info(project: EngineeringProject, part_id: str) -> dict:
    part = project.get_part_by_id(part_id)
    if part is None:
        raise ValueError(f"Unknown part id: {part_id}")
    if part.section_id is None:
        return {
            "part_id": part.id,
            "section_id": "",
            "section_name": "",
            "material_id": "",
            "material_name": "",
            "material_color": "",
            "unit_weight": 0.0,
            "thickness": 0.0,
            "plane_mode": "",
        }

    section = project.get_section_by_id(part.section_id)
    if section is None:
        raise ValueError(f"Part {part.id!r} references unknown section {part.section_id!r}")
    material = project.get_material_by_id(section.material_id)
    if material is None:
        raise ValueError(f"Section {section.id!r} references unknown material {section.material_id!r}")
    return {
        "part_id": part.id,
        "section_id": section.id,
        "section_name": section.name,
        "material_id": material.id,
        "material_name": material.name,
        "material_color": material.color,
        "unit_weight": material.unit_weight,
        "thickness": section.thickness,
        "plane_mode": section.plane_mode,
    }


def _create_unique_id(existing_ids: set[str], base_id: str) -> str:
    if base_id not in existing_ids:
        return base_id
    index = 2
    while True:
        candidate = f"{base_id}_{index}"
        if candidate not in existing_ids:
            return candidate
        index += 1

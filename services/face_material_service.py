from __future__ import annotations

from core.engineering.engineering_project import EngineeringProject
from core.engineering.part import Part
from services.material_manager_service import add_or_update_section, get_part_material_info


def assign_material_to_face(
    project: EngineeringProject,
    part_id: str,
    face_id: str,
    material_id: str,
    thickness: float,
) -> EngineeringProject:
    part = _require_part(project, part_id)
    face = _require_face(part, face_id)
    material = project.get_material_by_id(material_id)
    if material is None:
        raise ValueError(f"Unknown material id: {material_id}")
    section_id = add_or_update_section(
        project,
        name=f"{material.name}_{face.id}_section",
        material_id=material_id,
        thickness=float(thickness),
        plane_mode="stress",
    )
    face.section_id = section_id
    project.validate_references()
    return project


def assign_material_to_part(
    project: EngineeringProject,
    part_id: str,
    material_id: str,
    thickness: float,
) -> EngineeringProject:
    part = _require_part(project, part_id)
    material = project.get_material_by_id(material_id)
    if material is None:
        raise ValueError(f"Unknown material id: {material_id}")
    section_id = add_or_update_section(
        project,
        name=f"{material.name}_section",
        material_id=material_id,
        thickness=float(thickness),
        plane_mode="stress",
    )
    part.section_id = section_id
    for face in part.geometry.faces:
        face.section_id = section_id
    project.validate_references()
    return project


def get_face_material_info(
    project: EngineeringProject,
    part_id: str,
    face_id: str,
) -> dict:
    part = _require_part(project, part_id)
    face = _require_face(part, face_id)
    section_id = face.section_id or part.section_id or ""
    if not section_id:
        return _empty_face_info(part.id, face.id)
    section = project.get_section_by_id(section_id)
    if section is None:
        raise ValueError(f"Face {face.id!r} references unknown section {section_id!r}")
    material = project.get_material_by_id(section.material_id)
    if material is None:
        raise ValueError(f"Section {section.id!r} references unknown material {section.material_id!r}")
    return {
        "part_id": part.id,
        "face_id": face.id,
        "section_id": section.id,
        "material_id": material.id,
        "material_name": material.name,
        "material_color": material.color,
        "thickness": section.thickness,
        "plane_mode": section.plane_mode,
        "source": "face" if face.section_id else "part",
    }


def get_part_face_material_rows(project: EngineeringProject, part_id: str) -> list[dict]:
    part = _require_part(project, part_id)
    rows = []
    for face in part.geometry.faces:
        rows.append(get_face_material_info(project, part.id, face.id))
    return rows


def get_part_default_and_face_material_state(project: EngineeringProject, part_id: str) -> dict:
    part_info = get_part_material_info(project, part_id)
    return {
        "part": part_info,
        "faces": get_part_face_material_rows(project, part_id),
    }


def resolve_section_id_for_face(part: Part, face_id: str | None) -> str | None:
    if face_id:
        for face in part.geometry.faces:
            if face.id == face_id and face.section_id:
                return face.section_id
    return part.section_id


def _require_part(project: EngineeringProject, part_id: str) -> Part:
    part = project.get_part_by_id(part_id)
    if part is None:
        raise ValueError(f"Unknown part id: {part_id}")
    return part


def _require_face(part: Part, face_id: str):
    for face in part.geometry.faces:
        if face.id == face_id:
            return face
    raise ValueError(f"Unknown face id: {face_id}")


def _empty_face_info(part_id: str, face_id: str) -> dict:
    return {
        "part_id": part_id,
        "face_id": face_id,
        "section_id": "",
        "material_id": "",
        "material_name": "",
        "material_color": "",
        "thickness": 0.0,
        "plane_mode": "",
        "source": "none",
    }

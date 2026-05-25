from __future__ import annotations

from core.engineering.material_definition import MaterialDefinition
from core.engineering.section import SectionDefinition
from core.fem.material import Material


def map_section_to_solver_material(
    section: SectionDefinition,
    materials: list[MaterialDefinition],
    solver_material_id: int,
) -> tuple[Material, dict[str, int]]:
    material = _get_material_by_id(materials, section.material_id)
    if material is None:
        raise ValueError(
            f"Section {section.id!r} references unknown material {section.material_id!r}"
        )
    if section.plane_mode != "stress":
        raise ValueError("Only plane_mode='stress' is supported by the current FEM compiler")

    solver_material = Material(
        id=solver_material_id,
        name=material.name,
        young_modulus=material.young_modulus,
        poisson_ratio=material.poisson_ratio,
        thickness=section.thickness,
        plane_mode=section.plane_mode,
        color=material.color,
    )
    return solver_material, {section.id: solver_material.id}


def _get_material_by_id(
    materials: list[MaterialDefinition],
    material_id: str,
) -> MaterialDefinition | None:
    for material in materials:
        if material.id == material_id:
            return material
    return None

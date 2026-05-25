from __future__ import annotations

from core.engineering.engineering_project import EngineeringProject
from core.engineering.mesh_model import MeshModel
from core.meshing.rectangular_mesher import generate_rectangular_tri_mesh


def generate_mesh_for_part(
    project: EngineeringProject,
    part_id: str,
    nx: int,
    ny: int,
) -> MeshModel:
    part = project.get_part_by_id(part_id)
    if part is None:
        raise ValueError(f"Part {part_id!r} does not exist")

    return generate_rectangular_tri_mesh(geometry=part.geometry, nx=nx, ny=ny)

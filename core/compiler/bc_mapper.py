from __future__ import annotations

from core.engineering.boundary_condition_definition import BoundaryConditionDefinition
from core.engineering.mesh_model import MeshModel
from core.fem.constraint import Constraint


def map_boundary_condition_to_constraints(
    boundary_condition: BoundaryConditionDefinition,
    mesh: MeshModel,
    mesh_node_to_fem_node_id: dict[int, int],
    start_constraint_id: int,
) -> tuple[list[Constraint], int]:
    if boundary_condition.target_type != "geometry_edge":
        raise ValueError("Only target_type='geometry_edge' boundary conditions are supported")

    mesh_node_ids = mesh.geometry_edge_to_mesh_node_ids.get(boundary_condition.target_id)
    if mesh_node_ids is None:
        raise ValueError(
            f"Boundary condition {boundary_condition.id!r} references unknown geometry edge "
            f"{boundary_condition.target_id!r}"
        )
    if not mesh_node_ids:
        raise ValueError(
            f"Boundary condition {boundary_condition.id!r} target edge has no mesh nodes"
        )
    if not boundary_condition.ux_fixed and not boundary_condition.uy_fixed:
        raise ValueError(
            f"Boundary condition {boundary_condition.id!r} must fix at least one direction"
        )

    constraints: list[Constraint] = []
    next_constraint_id = start_constraint_id
    for mesh_node_id in mesh_node_ids:
        fem_node_id = mesh_node_to_fem_node_id.get(mesh_node_id)
        if fem_node_id is None:
            raise ValueError(f"Mesh node {mesh_node_id!r} has no FEM node mapping")

        constraints.append(
            Constraint(
                id=next_constraint_id,
                node_id=fem_node_id,
                ux_fixed=boundary_condition.ux_fixed,
                uy_fixed=boundary_condition.uy_fixed,
                ux_value=boundary_condition.ux_value,
                uy_value=boundary_condition.uy_value,
            )
        )
        next_constraint_id += 1

    return constraints, next_constraint_id

from __future__ import annotations

import math

from core.engineering.mesh_model import MeshModel
from core.fem.load import Load


def map_gravity_load_to_nodal_loads(
    mesh: MeshModel,
    mesh_node_to_fem_node_id: dict[int, int],
    element_unit_weights: dict[int, float],
    element_thicknesses: dict[int, float],
    start_load_id: int,
    direction_x: float = 0.0,
    direction_y: float = -1.0,
) -> tuple[list[Load], int, dict[str, float]]:
    direction_length = math.hypot(direction_x, direction_y)
    if direction_length <= 1.0e-12:
        raise ValueError("Gravity direction must not be zero")

    unit_dir_x = direction_x / direction_length
    unit_dir_y = direction_y / direction_length

    accumulated_forces: dict[int, list[float]] = {}
    active_element_count = 0
    total_fx = 0.0
    total_fy = 0.0

    for element in mesh.elements:
        unit_weight = float(element_unit_weights.get(element.id, 0.0) or 0.0)
        thickness = float(element_thicknesses.get(element.id, 0.0) or 0.0)
        if unit_weight <= 0.0 or thickness <= 0.0:
            continue

        area = _triangle_area(mesh, element.node_ids)
        if area <= 0.0:
            continue

        active_element_count += 1
        total_weight = unit_weight * area * thickness
        element_fx = total_weight * unit_dir_x
        element_fy = total_weight * unit_dir_y
        total_fx += element_fx
        total_fy += element_fy

        node_fx = element_fx / 3.0
        node_fy = element_fy / 3.0
        for mesh_node_id in element.node_ids:
            fem_node_id = mesh_node_to_fem_node_id.get(mesh_node_id)
            if fem_node_id is None:
                raise ValueError(f"Mesh node {mesh_node_id!r} has no FEM node mapping")
            force = accumulated_forces.setdefault(fem_node_id, [0.0, 0.0])
            force[0] += node_fx
            force[1] += node_fy

    loads: list[Load] = []
    next_load_id = start_load_id
    for fem_node_id in sorted(accumulated_forces):
        fx, fy = accumulated_forces[fem_node_id]
        if abs(fx) <= 1.0e-16 and abs(fy) <= 1.0e-16:
            continue
        loads.append(Load(id=next_load_id, node_id=fem_node_id, fx=fx, fy=fy))
        next_load_id += 1

    return loads, next_load_id, {
        "active_element_count": float(active_element_count),
        "total_fx": total_fx,
        "total_fy": total_fy,
    }


def _triangle_area(mesh: MeshModel, node_ids: list[int]) -> float:
    node_a = mesh.get_node_by_id(node_ids[0])
    node_b = mesh.get_node_by_id(node_ids[1])
    node_c = mesh.get_node_by_id(node_ids[2])
    if node_a is None or node_b is None or node_c is None:
        raise ValueError(f"Mesh element references unknown nodes: {node_ids!r}")
    signed_area = 0.5 * (
        (node_b.x - node_a.x) * (node_c.y - node_a.y)
        - (node_c.x - node_a.x) * (node_b.y - node_a.y)
    )
    return abs(signed_area)

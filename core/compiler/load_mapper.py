from __future__ import annotations

import math

from core.engineering.load_definition import LoadDefinition
from core.engineering.mesh_model import MeshModel
from core.fem.load import Load


def map_edge_uniform_load_to_nodal_loads(
    load: LoadDefinition,
    mesh: MeshModel,
    mesh_node_to_fem_node_id: dict[int, int],
    thickness: float,
    start_load_id: int,
) -> tuple[list[Load], int]:
    if load.target_type != "geometry_edge":
        raise ValueError("Only target_type='geometry_edge' loads are supported")
    if load.load_type != "edge_uniform":
        raise ValueError("Only load_type='edge_uniform' loads are supported")
    if load.qx == 0.0 and load.qy == 0.0:
        return [], start_load_id

    element_edges = mesh.geometry_edge_to_mesh_element_edges.get(load.target_id)
    if element_edges is None:
        raise ValueError(
            f"Load {load.id!r} references unknown geometry edge {load.target_id!r}"
        )
    if not element_edges:
        raise ValueError(f"Load {load.id!r} target edge has no mesh element edges")

    accumulated_forces: dict[int, list[float]] = {}
    for element_id, local_a, local_b in element_edges:
        element = mesh.get_element_by_id(element_id)
        if element is None:
            raise ValueError(f"Load {load.id!r} references unknown mesh element {element_id!r}")

        mesh_node_id_a = element.node_ids[local_a]
        mesh_node_id_b = element.node_ids[local_b]
        node_a = mesh.get_node_by_id(mesh_node_id_a)
        node_b = mesh.get_node_by_id(mesh_node_id_b)
        if node_a is None or node_b is None:
            raise ValueError(f"Load {load.id!r} references an unknown mesh node")

        edge_length = math.hypot(node_b.x - node_a.x, node_b.y - node_a.y)
        equivalent_fx = load.qx * edge_length * thickness / 2.0
        equivalent_fy = load.qy * edge_length * thickness / 2.0

        for mesh_node_id in (mesh_node_id_a, mesh_node_id_b):
            fem_node_id = mesh_node_to_fem_node_id.get(mesh_node_id)
            if fem_node_id is None:
                raise ValueError(f"Mesh node {mesh_node_id!r} has no FEM node mapping")

            force = accumulated_forces.setdefault(fem_node_id, [0.0, 0.0])
            force[0] += equivalent_fx
            force[1] += equivalent_fy

    loads: list[Load] = []
    next_load_id = start_load_id
    for fem_node_id in sorted(accumulated_forces):
        fx, fy = accumulated_forces[fem_node_id]
        if fx == 0.0 and fy == 0.0:
            continue
        loads.append(Load(id=next_load_id, node_id=fem_node_id, fx=fx, fy=fy))
        next_load_id += 1

    return loads, next_load_id

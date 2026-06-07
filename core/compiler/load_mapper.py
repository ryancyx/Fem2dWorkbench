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
    if load.target_type not in {"geometry_edge", "geometry_edge_segment"}:
        raise ValueError("Only geometry edge loads are supported")
    if load.load_type != "edge_uniform":
        raise ValueError("Only load_type='edge_uniform' loads are supported")
    if load.qx == 0.0 and load.qy == 0.0:
        return [], start_load_id

    mesh_node_ids = mesh.geometry_edge_to_mesh_node_ids.get(load.target_id)
    element_edges = mesh.geometry_edge_to_mesh_element_edges.get(load.target_id)
    if mesh_node_ids is None or element_edges is None:
        raise ValueError(
            f"Load {load.id!r} references unknown geometry edge {load.target_id!r}"
        )
    if len(mesh_node_ids) < 2 or not element_edges:
        raise ValueError(f"Load {load.id!r} target edge has no mesh element edges")

    start_t = 0.0 if load.target_type == "geometry_edge" else load.start_t
    end_t = 1.0 if load.target_type == "geometry_edge" else load.end_t
    if end_t - start_t <= 1.0e-9:
        raise ValueError(f"Load {load.id!r} target edge segment is too short")

    boundary_pairs = _build_boundary_pair_index(mesh, element_edges)
    edge_segments = _edge_segments_with_parameters(mesh, mesh_node_ids)
    accumulated_forces: dict[int, list[float]] = {}
    loaded_segment_count = 0
    for mesh_node_id_a, mesh_node_id_b, seg_start_t, seg_end_t, edge_length in edge_segments:
        if frozenset((mesh_node_id_a, mesh_node_id_b)) not in boundary_pairs:
            raise ValueError(
                f"Load {load.id!r} edge segment {mesh_node_id_a}-{mesh_node_id_b} is not mapped to a mesh boundary edge"
            )
        overlap_start = max(start_t, seg_start_t)
        overlap_end = min(end_t, seg_end_t)
        overlap_ratio = (overlap_end - overlap_start) / max(seg_end_t - seg_start_t, 1.0e-12)
        if overlap_ratio <= 1.0e-12:
            continue
        loaded_segment_count += 1
        loaded_length = edge_length * overlap_ratio
        equivalent_fx = load.qx * loaded_length * thickness / 2.0
        equivalent_fy = load.qy * loaded_length * thickness / 2.0

        for mesh_node_id in (mesh_node_id_a, mesh_node_id_b):
            fem_node_id = mesh_node_to_fem_node_id.get(mesh_node_id)
            if fem_node_id is None:
                raise ValueError(f"Mesh node {mesh_node_id!r} has no FEM node mapping")

            force = accumulated_forces.setdefault(fem_node_id, [0.0, 0.0])
            force[0] += equivalent_fx
            force[1] += equivalent_fy

    if loaded_segment_count == 0:
        raise ValueError(f"Load {load.id!r} target edge segment does not overlap any mesh boundary edge")

    loads: list[Load] = []
    next_load_id = start_load_id
    for fem_node_id in sorted(accumulated_forces):
        fx, fy = accumulated_forces[fem_node_id]
        if fx == 0.0 and fy == 0.0:
            continue
        loads.append(Load(id=next_load_id, node_id=fem_node_id, fx=fx, fy=fy))
        next_load_id += 1

    return loads, next_load_id


def _build_boundary_pair_index(
    mesh: MeshModel,
    element_edges: list[tuple[int, int, int]],
) -> set[frozenset[int]]:
    pairs: set[frozenset[int]] = set()
    for element_id, local_a, local_b in element_edges:
        element = mesh.get_element_by_id(element_id)
        if element is None:
            raise ValueError(f"Unknown mesh element {element_id!r} in geometry edge mapping")
        pairs.add(frozenset((element.node_ids[local_a], element.node_ids[local_b])))
    return pairs


def _edge_segments_with_parameters(
    mesh: MeshModel,
    mesh_node_ids: list[int],
) -> list[tuple[int, int, float, float, float]]:
    cumulative = [0.0]
    segment_lengths: list[float] = []
    for node_a_id, node_b_id in zip(mesh_node_ids[:-1], mesh_node_ids[1:]):
        node_a = mesh.get_node_by_id(node_a_id)
        node_b = mesh.get_node_by_id(node_b_id)
        if node_a is None or node_b is None:
            raise ValueError("Geometry edge mapping references an unknown mesh node")
        length = math.hypot(node_b.x - node_a.x, node_b.y - node_a.y)
        segment_lengths.append(length)
        cumulative.append(cumulative[-1] + length)

    total_length = cumulative[-1]
    if total_length <= 1.0e-12:
        raise ValueError("Geometry edge mapping has zero total length")

    rows: list[tuple[int, int, float, float, float]] = []
    for index, (node_a_id, node_b_id) in enumerate(zip(mesh_node_ids[:-1], mesh_node_ids[1:])):
        seg_start_t = cumulative[index] / total_length
        seg_end_t = cumulative[index + 1] / total_length
        rows.append((node_a_id, node_b_id, seg_start_t, seg_end_t, segment_lengths[index]))
    return rows


def map_nodal_concentrated_load_to_nodal_loads(
    load: LoadDefinition,
    mesh: MeshModel,
    mesh_node_to_fem_node_id: dict[int, int],
    start_load_id: int,
) -> tuple[list[Load], int]:
    if load.target_type != "geometry_point":
        raise ValueError("Only target_type='geometry_point' nodal loads are supported")
    if load.load_type != "nodal_concentrated":
        raise ValueError("Only load_type='nodal_concentrated' loads are supported")
    if load.qx == 0.0 and load.qy == 0.0:
        return [], start_load_id

    mesh_node_ids = mesh.geometry_point_to_mesh_node_ids.get(load.target_id)
    if mesh_node_ids is None or not mesh_node_ids:
        raise ValueError(
            f"Load {load.id!r} references unknown or unmapped geometry point {load.target_id!r}"
        )
    fem_node_id = mesh_node_to_fem_node_id.get(mesh_node_ids[0])
    if fem_node_id is None:
        raise ValueError(f"Mesh node {mesh_node_ids[0]!r} has no FEM node mapping")

    return [Load(id=start_load_id, node_id=fem_node_id, fx=load.qx, fy=load.qy)], start_load_id + 1

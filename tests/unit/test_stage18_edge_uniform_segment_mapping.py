from __future__ import annotations

import pytest

from core.compiler.load_mapper import map_edge_uniform_load_to_nodal_loads
from core.engineering.geometry import GeometryModel
from core.engineering.load_definition import LoadDefinition
from core.meshing.rectangular_mesher import generate_rectangular_tri_mesh


def _build_mesh():
    geometry = GeometryModel.create_rectangle(width=2.0, height=1.0)
    mesh = generate_rectangular_tri_mesh(geometry, nx=4, ny=1)
    node_mapping = {node.id: node.id for node in mesh.nodes}
    return mesh, node_mapping


def _sum_loads(loads):
    return sum(load.fx for load in loads), sum(load.fy for load in loads)


def test_stage18_edge_uniform_segment_mapping_full_edge_matches_default() -> None:
    mesh, node_mapping = _build_mesh()
    default_load = LoadDefinition(
        id="load_default",
        name="default",
        step_id="step_static",
        target_type="geometry_edge",
        target_id="top",
        load_type="edge_uniform",
        qx=0.0,
        qy=-1000.0,
    )
    explicit_full_load = LoadDefinition(
        id="load_full",
        name="full",
        step_id="step_static",
        target_type="geometry_edge",
        target_id="top",
        load_type="edge_uniform",
        qx=0.0,
        qy=-1000.0,
        start_t=0.0,
        end_t=1.0,
    )
    default_rows, _ = map_edge_uniform_load_to_nodal_loads(default_load, mesh, node_mapping, 0.01, 1)
    full_rows, _ = map_edge_uniform_load_to_nodal_loads(explicit_full_load, mesh, node_mapping, 0.01, 1)
    assert len(default_rows) == len(full_rows)
    for left, right in zip(default_rows, full_rows):
        assert left.node_id == right.node_id
        assert left.fx == pytest.approx(right.fx)
        assert left.fy == pytest.approx(right.fy)


def test_stage18_edge_uniform_segment_mapping_partial_range_has_expected_resultant() -> None:
    mesh, node_mapping = _build_mesh()
    full_load = LoadDefinition(
        id="load_full",
        name="full",
        step_id="step_static",
        target_type="geometry_edge",
        target_id="top",
        load_type="edge_uniform",
        qx=0.0,
        qy=-1000.0,
        start_t=0.0,
        end_t=1.0,
    )
    half_load = LoadDefinition(
        id="load_half",
        name="half",
        step_id="step_static",
        target_type="geometry_edge",
        target_id="top",
        load_type="edge_uniform",
        qx=0.0,
        qy=-1000.0,
        start_t=0.25,
        end_t=0.75,
    )
    full_rows, _ = map_edge_uniform_load_to_nodal_loads(full_load, mesh, node_mapping, 0.01, 1)
    half_rows, _ = map_edge_uniform_load_to_nodal_loads(half_load, mesh, node_mapping, 0.01, 1)
    _, full_fy = _sum_loads(full_rows)
    _, half_fy = _sum_loads(half_rows)
    assert half_fy == pytest.approx(full_fy * 0.5)


def test_stage18_edge_uniform_segment_mapping_sorts_reversed_interval() -> None:
    reversed_load = LoadDefinition(
        id="load_reverse",
        name="reverse",
        step_id="step_static",
        target_type="geometry_edge",
        target_id="top",
        load_type="edge_uniform",
        qx=0.0,
        qy=-1000.0,
        start_t=0.8,
        end_t=0.2,
    )
    assert reversed_load.start_t == pytest.approx(0.2)
    assert reversed_load.end_t == pytest.approx(0.8)


def test_stage18_edge_uniform_segment_mapping_rejects_out_of_range_and_short_interval() -> None:
    with pytest.raises(ValueError):
        LoadDefinition(
            id="load_bad_1",
            name="bad_1",
            step_id="step_static",
            target_type="geometry_edge",
            target_id="top",
            load_type="edge_uniform",
            qx=0.0,
            qy=-1000.0,
            start_t=-0.1,
            end_t=0.8,
        )
    with pytest.raises(ValueError):
        LoadDefinition(
            id="load_bad_2",
            name="bad_2",
            step_id="step_static",
            target_type="geometry_edge",
            target_id="top",
            load_type="edge_uniform",
            qx=0.0,
            qy=-1000.0,
            start_t=0.5,
            end_t=0.5,
        )

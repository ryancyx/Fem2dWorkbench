from __future__ import annotations

import pytest

from agent.bc_load_agent import BC_LOAD_ACTION_SCHEMA, BCLoadAgent
from agent.geometry_agent import GeometryAgent
from agent.llm_client import StructuredOutputError
from agent.simulation_plan import SimulationPlan


def _build_rectangle(empty_project, valid_plan, fake_llm):
    GeometryAgent(fake_llm).create(valid_plan, empty_project)
    return empty_project


def test_bc_load_agent_applies_point_and_edge_definitions_to_real_project(
    empty_project,
    valid_plan,
    fake_llm,
) -> None:
    project = _build_rectangle(empty_project, valid_plan, fake_llm)
    valid_plan.point_constraints.append(
        {"target": {"selector": "bottom_left"}, "ux": None, "uy": 0.0}
    )
    valid_plan.point_loads.append(
        {"target": {"selector": "top_right"}, "vector": [5.0, -2.0]}
    )
    agent = BCLoadAgent(fake_llm)

    assert agent.apply(valid_plan, project)

    assert len(project.boundary_conditions) == 2
    edge_bc = next(row for row in project.boundary_conditions if row.target_type == "geometry_edge")
    point_bc = next(row for row in project.boundary_conditions if row.target_type == "geometry_point")
    assert edge_bc.target_id == "left"
    assert edge_bc.ux_fixed and edge_bc.uy_fixed
    assert point_bc.target_id == "p1"
    assert not point_bc.ux_fixed and point_bc.uy_fixed
    assert point_bc.uy_value == 0.0

    assert len(project.loads) == 2
    edge_load = next(row for row in project.loads if row.load_type == "edge_uniform")
    point_load = next(row for row in project.loads if row.load_type == "nodal_concentrated")
    assert (edge_load.target_id, edge_load.qx, edge_load.qy) == ("right", 100.0, 0.0)
    assert (point_load.target_id, point_load.qx, point_load.qy) == ("p3", 5.0, -2.0)
    project.validate_references()
    assert fake_llm.requests[-1][2] == BC_LOAD_ACTION_SCHEMA


def test_bc_load_agent_resolves_circle_outer_boundary_to_all_edges(
    empty_project,
    fake_llm,
) -> None:
    GeometryAgent(fake_llm).create_circle(0.0, 0.0, 1.0, empty_project)
    agent = BCLoadAgent(fake_llm)

    edge_ids = agent.resolve_target({"selector": "outer_boundary"}, "edge", empty_project)

    assert len(edge_ids) == 64
    assert len(set(edge_ids)) == 64


def test_bc_load_agent_rejects_unknown_target(empty_project, valid_plan, fake_llm) -> None:
    project = _build_rectangle(empty_project, valid_plan, fake_llm)
    agent = BCLoadAgent(fake_llm)

    with pytest.raises(ValueError, match="did not resolve"):
        agent.resolve_target({"selector": "diagonal"}, "edge", project)

    with pytest.raises(ValueError, match="Unknown geometry_point"):
        agent.add_point_load("missing", 1.0, 2.0, project)


def test_bc_load_apply_replaces_only_previous_agent_definitions(
    empty_project,
    valid_plan,
    fake_llm,
) -> None:
    project = _build_rectangle(empty_project, valid_plan, fake_llm)
    agent = BCLoadAgent(fake_llm)

    agent.apply(valid_plan, project)
    first_bc_ids = set(project.metadata["agent_boundary_condition_ids"])
    first_load_ids = set(project.metadata["agent_load_ids"])
    agent.apply(valid_plan, project)

    assert len(project.boundary_conditions) == 1
    assert len(project.loads) == 1
    assert set(project.metadata["agent_boundary_condition_ids"]) == first_bc_ids
    assert set(project.metadata["agent_load_ids"]) == first_load_ids


def test_bc_load_agent_rejects_llm_internal_entity_id(
    empty_project,
    valid_plan,
) -> None:
    from conftest import FakeLLMClient

    geometry_llm = FakeLLMClient(
        {
            "action": "create_rectangle",
            "parameters": {"width": 100.0, "height": 50.0, "originX": 0.0, "originY": 0.0},
        }
    )
    GeometryAgent(geometry_llm).create(valid_plan, empty_project)
    invalid_llm = FakeLLMClient(
        {
            "actions": [
                {
                    "action": "add_edge_constraint",
                    "target": {"edge_id": "left"},
                    "ux": 0.0,
                    "uy": 0.0,
                }
            ]
        }
    )

    with pytest.raises(StructuredOutputError, match="selector or coordinate"):
        BCLoadAgent(invalid_llm).apply(valid_plan, empty_project)
    assert empty_project.boundary_conditions == []


def _definition_snapshot(project):
    return (
        [row.to_dict() for row in project.boundary_conditions],
        [row.to_dict() for row in project.loads],
        list(project.metadata.get("agent_boundary_condition_ids", [])),
        list(project.metadata.get("agent_load_ids", [])),
    )


def test_invalid_llm_output_preserves_existing_agent_managed_definitions(
    empty_project,
    valid_plan,
    fake_llm,
) -> None:
    from conftest import FakeLLMClient

    project = _build_rectangle(empty_project, valid_plan, fake_llm)
    BCLoadAgent(fake_llm).apply(valid_plan, project)
    before = _definition_snapshot(project)

    with pytest.raises(StructuredOutputError):
        BCLoadAgent(FakeLLMClient({"invalid": []})).apply(valid_plan, project)

    assert _definition_snapshot(project) == before


def test_unresolvable_selector_preserves_existing_agent_managed_definitions(
    empty_project,
    valid_plan,
    fake_llm,
) -> None:
    project = _build_rectangle(empty_project, valid_plan, fake_llm)
    agent = BCLoadAgent(fake_llm)
    agent.apply(valid_plan, project)
    before = _definition_snapshot(project)
    invalid_data = valid_plan.to_dict()
    invalid_data["edgeConstraints"][0]["target"] = {"selector": "diagonal"}
    invalid_plan = SimulationPlan.from_dict(invalid_data)

    with pytest.raises(ValueError, match="did not resolve"):
        agent.apply(invalid_plan, project)

    assert _definition_snapshot(project) == before


def test_coordinate_targets_require_geometry_scaled_proximity(
    empty_project,
    valid_plan,
    fake_llm,
) -> None:
    project = _build_rectangle(empty_project, valid_plan, fake_llm)
    agent = BCLoadAgent(fake_llm)

    assert agent.resolve_target({"coordinate": [0.0, 0.0]}, "point", project) == ["p1"]
    assert agent.resolve_target({"coordinate": [0.00005, 0.0]}, "point", project) == ["p1"]
    assert agent.resolve_target({"coordinate": [50.0, 0.0]}, "edge", project) == ["bottom"]
    assert agent.resolve_target({"coordinate": [50.0, 0.00005]}, "edge", project) == ["bottom"]

    with pytest.raises(ValueError, match="did not resolve"):
        agent.resolve_target({"coordinate": [1000.0, 1000.0]}, "point", project)
    with pytest.raises(ValueError, match="did not resolve"):
        agent.resolve_target({"coordinate": [1000.0, 1000.0]}, "edge", project)


def test_far_coordinate_apply_does_not_create_definitions(
    empty_project,
    valid_plan,
    fake_llm,
) -> None:
    project = _build_rectangle(empty_project, valid_plan, fake_llm)
    data = valid_plan.to_dict()
    data["edgeConstraints"] = []
    data["edgeLoads"] = []
    data["pointLoads"] = [
        {"target": {"coordinate": [1000.0, 1000.0]}, "vector": [1.0, 2.0]}
    ]
    far_plan = SimulationPlan.from_dict(data)

    with pytest.raises(ValueError, match="did not resolve"):
        BCLoadAgent(fake_llm).apply(far_plan, project)

    assert project.boundary_conditions == []
    assert project.loads == []

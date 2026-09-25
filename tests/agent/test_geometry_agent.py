from __future__ import annotations

import pytest

from agent.geometry_agent import GEOMETRY_ACTION_SCHEMA, GeometryAgent
from agent.llm_client import StructuredOutputError
from agent.simulation_plan import SimulationPlan


def _plan(geometry: dict) -> SimulationPlan:
    return SimulationPlan(
        version=1,
        geometry=geometry,
        material={
            "name": "steel",
            "E": 210e9,
            "nu": 0.3,
            "thickness": 0.01,
            "plane_mode": "stress",
        },
        mesh_size=0.2,
    )


def test_geometry_agent_creates_rectangle_in_real_project(empty_project, fake_llm) -> None:
    agent = GeometryAgent(fake_llm)

    assert agent.create(_plan({"type": "rectangle", "width": 4.0, "height": 2.0}), empty_project)

    part = empty_project.get_part_by_id(empty_project.metadata["active_part_id"])
    assert part is not None
    assert [(point.x, point.y) for point in part.geometry.points] == [
        (0.0, 0.0),
        (4.0, 0.0),
        (4.0, 2.0),
        (0.0, 2.0),
    ]
    assert {edge.id for edge in part.geometry.edges} == {"bottom", "right", "top", "left"}
    assert fake_llm.requests[-1][2] == GEOMETRY_ACTION_SCHEMA


def test_geometry_agent_creates_fixed_64_segment_circle(empty_project, fake_llm) -> None:
    agent = GeometryAgent(fake_llm)

    assert agent.create(
        _plan({"type": "circle", "centerX": 2.0, "centerY": -1.0, "radius": 3.0}),
        empty_project,
    )

    part = empty_project.get_part_by_id(empty_project.metadata["active_part_id"])
    assert part is not None
    assert len(part.geometry.points) == 64
    assert len(part.geometry.edges) == 64
    assert len(part.geometry.faces) == 1
    assert part.geometry.points[0].x == pytest.approx(5.0)
    assert part.geometry.points[0].y == pytest.approx(-1.0)


def test_geometry_agent_reuses_only_its_managed_part(empty_project, fake_llm) -> None:
    agent = GeometryAgent(fake_llm)
    first = _plan({"type": "rectangle", "width": 4.0, "height": 2.0})
    second = _plan({"type": "rectangle", "width": 8.0, "height": 3.0})

    agent.create(first, empty_project)
    managed_id = empty_project.metadata["agent_managed_part_id"]
    agent.create(second, empty_project)

    assert len(empty_project.parts) == 1
    assert empty_project.parts[0].id == managed_id
    assert empty_project.parts[0].geometry.points[2].x == 8.0
    assert empty_project.parts[0].geometry.points[2].y == 3.0


def test_geometry_agent_rejects_llm_action_that_changes_validated_plan(empty_project) -> None:
    from conftest import FakeLLMClient

    llm = FakeLLMClient(
        {
            "action": "create_rectangle",
            "parameters": {"width": 999.0, "height": 2.0, "originX": 0.0, "originY": 0.0},
        }
    )

    with pytest.raises(StructuredOutputError, match="preserve"):
        GeometryAgent(llm).create(
            _plan({"type": "rectangle", "width": 4.0, "height": 2.0}),
            empty_project,
        )
    assert empty_project.parts == []

from __future__ import annotations

import json

import pytest

from agent.architect_agent import ArchitectAgent, SIMULATION_PLAN_SCHEMA
from agent.llm_client import StructuredOutputError


def test_architect_agent_creates_valid_plan_from_structured_output(
    empty_project,
    valid_plan,
) -> None:
    from conftest import FakeLLMClient

    llm = FakeLLMClient(valid_plan.to_dict())
    architect = ArchitectAgent(llm)

    plan = architect.create_plan("Create a plate", empty_project)

    assert plan == valid_plan
    assert llm.requests[0][2] == SIMULATION_PLAN_SCHEMA
    content = json.loads(llm.requests[0][1])
    assert content["mode"] == "create"
    assert content["projectContext"]["defaultSection"] == {
        "thickness": 0.01,
        "plane_mode": "stress",
    }


def test_architect_agent_revision_forces_next_version(empty_project, valid_plan) -> None:
    from conftest import FakeLLMClient

    response = valid_plan.to_dict()
    response["meshSize"] = 2.5
    response["version"] = 99
    llm = FakeLLMClient(response)

    revised = ArchitectAgent(llm).revise_plan("Use a finer mesh", valid_plan, empty_project)

    assert revised.version == 2
    assert revised.mesh_size == 2.5
    assert json.loads(llm.requests[0][1])["mode"] == "revise"


def test_architect_agent_rejects_invalid_structured_output(empty_project) -> None:
    from conftest import FakeLLMClient

    architect = ArchitectAgent(FakeLLMClient({"geometry": {"type": "rectangle"}}))

    with pytest.raises(StructuredOutputError, match="Invalid Architect structured output"):
        architect.create_plan("bad response", empty_project)

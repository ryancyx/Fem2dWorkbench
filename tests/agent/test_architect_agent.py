from __future__ import annotations

import json

import pytest

from agent.architect_agent import (
    ArchitectAgent,
    PLANE_STRAIN_UNSUPPORTED_MESSAGE,
    SIMULATION_PLAN_SCHEMA,
    UnsupportedCapabilityError,
)
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
    assert content["projectContext"]["agentCapabilities"]["planeModes"] == ["stress"]


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


def test_architect_stops_plane_strain_before_engineering_execution(
    empty_project,
    valid_plan,
) -> None:
    from conftest import FakeLLMClient

    response = valid_plan.to_dict()
    response["material"]["plane_mode"] = "strain"

    with pytest.raises(
        UnsupportedCapabilityError,
        match="仅支持平面应力",
    ) as error:
        ArchitectAgent(FakeLLMClient(response)).create_plan(
            "Use plane strain",
            empty_project,
        )

    assert str(error.value) == PLANE_STRAIN_UNSUPPORTED_MESSAGE


def test_architect_accepts_plane_stress_with_strain_result(
    empty_project,
    valid_plan,
) -> None:
    from conftest import FakeLLMClient

    response = valid_plan.to_dict()
    response["material"]["plane_mode"] = "stress"
    response["requestedResult"] = "strain"

    plan = ArchitectAgent(FakeLLMClient(response)).create_plan(
        "Use plane stress and show strain results",
        empty_project,
    )

    assert plan.material["plane_mode"] == "stress"
    assert plan.requested_result == "strain"


def test_plane_strain_confirmation_uses_architect_revision_path(
    empty_project,
    valid_plan,
) -> None:
    from conftest import FakeLLMClient

    responses = []
    strain_response = valid_plan.to_dict()
    strain_response["material"]["plane_mode"] = "strain"
    stress_response = valid_plan.to_dict()
    stress_response["material"]["plane_mode"] = "stress"

    def respond(_system_prompt, user_content, _schema):
        content = json.loads(user_content)
        responses.append(content)
        return strain_response if len(responses) == 1 else stress_response

    architect = ArchitectAgent(FakeLLMClient(respond))
    with pytest.raises(UnsupportedCapabilityError):
        architect.create_plan("Use plane strain", empty_project)

    revised = architect.create_plan("Yes, change it to plane stress", empty_project)

    assert [content["mode"] for content in responses] == ["create", "revise"]
    assert responses[1]["currentPlan"]["material"]["plane_mode"] == "strain"
    assert revised.version == 2
    assert revised.material["plane_mode"] == "stress"

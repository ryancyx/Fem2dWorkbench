from __future__ import annotations

from agent.architect_agent import PLANE_STRAIN_UNSUPPORTED_MESSAGE
from agent.workflow_factory import create_agent_workflow
from agent.workflow_state import WorkflowStage, WorkflowStatus


def test_plane_strain_waits_for_user_before_any_specialist_runs(
    empty_project,
    valid_plan,
) -> None:
    from conftest import FakeLLMClient

    response = valid_plan.to_dict()
    response["material"]["plane_mode"] = "strain"
    llm = FakeLLMClient(response)
    workflow = create_agent_workflow(empty_project, llm_client=llm)

    state = workflow.start("Use a plane strain analysis")

    assert state.status == WorkflowStatus.WAITING_USER_INPUT
    assert state.current_stage == WorkflowStage.ARCHITECT
    assert state.simulation_plan is None
    assert state.current_mesh is None
    assert state.execution_result is not None
    assert state.execution_result.stage == "ARCHITECT"
    assert state.execution_result.error_message == PLANE_STRAIN_UNSUPPORTED_MESSAGE
    assert [request[2]["title"] for request in llm.requests] == ["SimulationPlan"]

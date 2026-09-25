from __future__ import annotations

import os

import pytest

from agent.llm_client import LLMClient
from agent.llm_providers import create_llm_client
from agent.workflow_factory import create_agent_workflow
from agent.workflow_orchestrator import WorkflowOrchestrator
from agent.workflow_state import WorkflowStatus
from services.project_factory_service import create_empty_workbench_project


RUN_REAL_API = os.environ.get("FEM2D_AGENT_RUN_REAL_API") == "1"
pytestmark = pytest.mark.skipif(
    not RUN_REAL_API,
    reason="Set FEM2D_AGENT_RUN_REAL_API=1 with provider credentials to run real API tests",
)


class RecordingLLMClient:
    def __init__(self, delegate: LLMClient) -> None:
        self.delegate = delegate
        self.schema_titles: list[str] = []

    def request(self, system_prompt, user_content, schema):
        self.schema_titles.append(str(schema.get("title", "")))
        return self.delegate.request(system_prompt, user_content, schema)


def _orchestrator(recording_client: RecordingLLMClient) -> WorkflowOrchestrator:
    project = create_empty_workbench_project("real_agent_e2e")
    return create_agent_workflow(
        project,
        llm_client=recording_client,
        max_retries=2,
    )


def test_real_natural_language_backend_normal_case() -> None:
    llm = RecordingLLMClient(create_llm_client())
    orchestrator = _orchestrator(llm)

    state = orchestrator.start(
        "Create a 100 by 50 rectangle at the origin. Use material Steel with E=210000, "
        "nu=0.3, thickness=0.01 and plane stress. Fully fix the left edge and apply a "
        "uniform edge load [100, 0] on the right edge. Use mesh size 5 and request "
        "von Mises stress."
    )

    assert state.status == WorkflowStatus.COMPLETED, _state_diagnostics(state, llm)
    assert state.execution_result is not None and state.execution_result.success
    assert state.result_data is not None
    assert {"SimulationPlan", "GeometryAction", "MaterialActions", "BCLoadActions"}.issubset(
        set(llm.schema_titles)
    )


def test_real_reviewer_repair_loop_reaches_success_after_confirm() -> None:
    llm = RecordingLLMClient(create_llm_client())
    orchestrator = _orchestrator(llm)

    failed = orchestrator.start(
        "Create a 100 by 50 rectangle at the origin. Use material Steel with E=210000, "
        "nu=0.3, thickness=0.01 and plane stress. Do not add any point or edge displacement "
        "constraints: leave the model completely unconstrained in ux and uy. Apply a "
        "uniform edge load [100, 0] on the right edge. Use mesh size 5 and request von "
        "Mises stress. Preserve this intentionally unsupported model exactly so the "
        "Reviewer can diagnose all rigid-body modes after the real solve fails."
    )

    assert failed.status == WorkflowStatus.WAITING_APPROVAL, _state_diagnostics(failed, llm)
    assert failed.review_result is not None
    assert failed.review_result.has_problem
    assert failed.review_result.proposals
    assert "ReviewResult" in llm.schema_titles

    completed = orchestrator.handle_approval(True, 0)

    assert completed.status == WorkflowStatus.COMPLETED, _state_diagnostics(completed, llm)
    assert completed.simulation_plan is not None
    assert completed.simulation_plan.version == 2
    assert completed.retry_count == 1


def _state_diagnostics(state, llm: RecordingLLMClient) -> dict:
    return {
        "status": state.status.value,
        "stage": state.current_stage.value,
        "executionResult": (
            state.execution_result.to_dict() if state.execution_result is not None else None
        ),
        "schemaTitles": list(llm.schema_titles),
    }

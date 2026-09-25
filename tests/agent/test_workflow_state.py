from __future__ import annotations

from agent.execution_result import ExecutionResult
from agent.review_models import RepairProposal, ReviewResult
from agent.workflow_state import WorkflowStage, WorkflowState, WorkflowStatus


def test_workflow_state_round_trip(empty_project, valid_plan) -> None:
    state = WorkflowState(
        user_input="build a plate",
        project=empty_project,
        simulation_plan=valid_plan,
        current_stage=WorkflowStage.SOLVE,
        status=WorkflowStatus.RUNNING,
        execution_result=ExecutionResult.succeeded("MESH"),
        retry_count=1,
        max_retries=2,
    )

    restored = WorkflowState.from_dict(state.to_dict())

    assert restored.current_stage == WorkflowStage.SOLVE
    assert restored.status == WorkflowStatus.RUNNING
    assert restored.simulation_plan == valid_plan
    assert restored.project.to_dict() == empty_project.to_dict()
    assert restored.retry_count == 1


def test_workflow_state_transition_updates_approval_flag(empty_project) -> None:
    state = WorkflowState(user_input="", project=empty_project)

    state.transition(WorkflowStage.APPROVAL, WorkflowStatus.WAITING_APPROVAL)

    assert state.waiting_for_approval is True
    assert state.current_stage == WorkflowStage.APPROVAL


def test_waiting_approval_state_round_trip_preserves_review_and_diagnostics(
    empty_project,
    valid_plan,
) -> None:
    review = ReviewResult(
        has_problem=True,
        diagnosis="The solve is singular.",
        evidence=("No uy restraint exists.",),
        proposals=(
            RepairProposal(
                title="Add uy restraint",
                reason="Remove rigid translation.",
                changes={
                    "operation": "add_point_constraint",
                    "target": {"selector": "bottom_left"},
                    "ux": None,
                    "uy": 0.0,
                },
            ),
        ),
    )
    state = WorkflowState(
        user_input="build",
        project=empty_project,
        simulation_plan=valid_plan,
        current_stage=WorkflowStage.APPROVAL,
        status=WorkflowStatus.WAITING_APPROVAL,
        execution_result=ExecutionResult.failed(
            "SOLVE",
            RuntimeError("SingularMatrix"),
            solve_result={"mesh": {"exists": True, "nodeCount": 8, "elementCount": 6}},
        ),
        review_result=review,
        waiting_for_approval=True,
    )

    restored = WorkflowState.from_dict(state.to_dict())

    assert restored.status == WorkflowStatus.WAITING_APPROVAL
    assert restored.waiting_for_approval is True
    assert restored.review_result == review
    assert restored.execution_result is not None
    assert restored.execution_result.solve_result == {
        "mesh": {"exists": True, "nodeCount": 8, "elementCount": 6}
    }

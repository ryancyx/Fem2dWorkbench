from __future__ import annotations

from types import SimpleNamespace

import pytest

from agent.review_models import RepairProposal, ReviewResult
from agent.simulation_plan import SimulationPlan
from agent.workflow_orchestrator import WorkflowOrchestrator
from agent.workflow_state import WorkflowStage, WorkflowStatus
from core.engineering.boundary_condition_definition import BoundaryConditionDefinition
from services.part_edit_service import add_rectangle_part


class FakeArchitect:
    def __init__(
        self,
        plan,
        calls: list[str],
        *,
        fail: bool = False,
        revised_plan=None,
    ) -> None:
        self.plan = plan
        self.calls = calls
        self.fail = fail
        self.revised_plan = revised_plan or plan

    def create_plan(self, _text, _project):
        self.calls.append("architect")
        if self.fail:
            raise ValueError("planning failed")
        return self.plan

    def revise_plan(self, _text, _plan, _project):
        self.calls.append("architect_revise")
        return self.revised_plan


class FakeSpecialist:
    def __init__(self, label: str, calls: list[str], *, fail: bool = False) -> None:
        self.label = label
        self.calls = calls
        self.fail = fail

    def create(self, _plan, _project):
        self.calls.append(self.label)
        if self.fail:
            raise ValueError(f"{self.label} failed")
        return True

    def apply(self, _plan, _project):
        self.calls.append(self.label)
        if self.fail:
            raise ValueError(f"{self.label} failed")
        return True

    def clear_managed_definitions(self, _project):
        return None


class FakeReviewer:
    def __init__(self, result: ReviewResult, calls: list[str]) -> None:
        self.result = result
        self.calls = calls

    def review(self, _plan, _project, _execution_result):
        self.calls.append("review")
        return self.result


def _orchestrator(
    empty_project,
    valid_plan,
    *,
    fail_stage: str | None = None,
    reviewer=None,
    max_retries: int = 2,
):
    calls: list[str] = []
    add_rectangle_part(empty_project, "fake_geometry", 1.0, 1.0)
    empty_project.add_boundary_condition(
        BoundaryConditionDefinition(
            id="workflow_test_bc",
            name="workflow test restraint",
            step_id=empty_project.analysis_steps[0].id,
            target_type="geometry_edge",
            target_id="e1",
            ux_fixed=True,
            uy_fixed=True,
        )
    )

    def mesh_generator(_geometry, **kwargs):
        calls.append("mesh")
        if fail_stage == "mesh":
            raise RuntimeError("mesh failed")
        assert kwargs["target_size"] == valid_plan.mesh_size
        return SimpleNamespace(nodes=[], elements=[])

    def compiler(*, project, mesh, step_id):
        calls.append("compile")
        assert project is empty_project
        assert step_id == "step_static"
        return SimpleNamespace(fem_model=object(), warnings=[])

    def solver(_model):
        calls.append("solve")
        if fail_stage == "solve":
            raise RuntimeError("singular matrix")
        return object()

    def result_builder(_solution, requested_result):
        calls.append("result")
        return {"requestedResult": requested_result}

    orchestrator = WorkflowOrchestrator(
        project=empty_project,
        architect_agent=FakeArchitect(valid_plan, calls, fail=fail_stage == "architect"),
        geometry_agent=FakeSpecialist("geometry", calls, fail=fail_stage == "geometry"),
        material_agent=FakeSpecialist("material", calls, fail=fail_stage == "material"),
        bc_load_agent=FakeSpecialist("bc_load", calls, fail=fail_stage == "bc_load"),
        reviewer_agent=reviewer,
        mesh_generator=mesh_generator,
        compiler=compiler,
        solver=solver,
        result_builder=result_builder,
        max_retries=max_retries,
    )
    return orchestrator, calls


def test_unrestrained_static_model_routes_to_reviewer_after_compile(
    empty_project,
    valid_plan,
) -> None:
    review = ReviewResult(
        has_problem=True,
        diagnosis="The model has no displacement restraints.",
        evidence=("No boundary condition restrains ux or uy.",),
        proposals=(
            RepairProposal(
                title="Fully fix the left edge",
                reason="Remove the two translations and in-plane rotation.",
                changes={
                    "operation": "add_edge_constraint",
                    "target": {"selector": "left"},
                    "ux": 0.0,
                    "uy": 0.0,
                },
            ),
        ),
    )
    calls: list[str] = []
    add_rectangle_part(empty_project, "fake_geometry", 1.0, 1.0)
    orchestrator = WorkflowOrchestrator(
        project=empty_project,
        architect_agent=FakeArchitect(valid_plan, calls),
        geometry_agent=FakeSpecialist("geometry", calls),
        material_agent=FakeSpecialist("material", calls),
        bc_load_agent=FakeSpecialist("bc_load", calls),
        reviewer_agent=FakeReviewer(review, calls),
        mesh_generator=lambda _geometry, **_kwargs: SimpleNamespace(nodes=[], elements=[]),
        compiler=lambda **_kwargs: (
            calls.append("compile") or SimpleNamespace(fem_model=object(), warnings=[])
        ),
        solver=lambda _model: calls.append("solve") or object(),
        result_builder=lambda _solution, _requested: {},
    )

    state = orchestrator.start("build an intentionally unrestrained model")

    assert state.status == WorkflowStatus.WAITING_APPROVAL
    assert state.current_stage == WorkflowStage.APPROVAL
    assert "review" in calls
    assert state.execution_result is not None
    assert state.execution_result.stage == "SOLVE"
    assert "no displacement restraints" in state.execution_result.error_message
    assert "compile" in calls
    assert "solve" not in calls


def test_orchestrator_runs_deterministic_success_path_in_order(empty_project, valid_plan) -> None:
    orchestrator, calls = _orchestrator(empty_project, valid_plan)

    state = orchestrator.start("build and solve")

    assert calls == ["architect", "geometry", "material", "bc_load", "mesh", "compile", "solve", "result"]
    assert state.status == WorkflowStatus.COMPLETED
    assert state.current_stage == WorkflowStage.RESULT
    assert state.execution_result is not None and state.execution_result.success
    assert state.result_data == {"requestedResult": "von_mises"}


def test_plane_stress_analysis_can_request_strain_result(empty_project, valid_plan) -> None:
    data = valid_plan.to_dict()
    data["material"]["plane_mode"] = "stress"
    data["requestedResult"] = "strain"
    plan = SimulationPlan.from_dict(data)
    orchestrator, calls = _orchestrator(empty_project, plan)

    state = orchestrator.start("Run plane stress and return strain results")

    assert calls == [
        "architect",
        "geometry",
        "material",
        "bc_load",
        "mesh",
        "compile",
        "solve",
        "result",
    ]
    assert state.status == WorkflowStatus.COMPLETED
    assert state.result_data == {"requestedResult": "strain"}


@pytest.mark.parametrize(
    ("fail_stage", "last_call", "execution_stage"),
    [
        ("geometry", "geometry", "GEOMETRY"),
        ("material", "material", "MATERIAL"),
        ("bc_load", "bc_load", "BC_LOAD"),
        ("mesh", "mesh", "MESH"),
        ("solve", "solve", "SOLVE"),
    ],
)
def test_orchestrator_routes_diagnosable_execution_failures_to_review(
    empty_project,
    valid_plan,
    fail_stage,
    last_call,
    execution_stage,
) -> None:
    orchestrator, calls = _orchestrator(empty_project, valid_plan, fail_stage=fail_stage)

    state = orchestrator.start("build")

    assert calls[-1] == last_call
    assert "result" not in calls
    assert state.status == WorkflowStatus.RUNNING
    assert state.current_stage == WorkflowStage.REVIEW
    assert state.execution_result is not None
    assert state.execution_result.stage == execution_stage


def test_orchestrator_routes_solver_failure_to_review(empty_project, valid_plan) -> None:
    orchestrator, calls = _orchestrator(empty_project, valid_plan, fail_stage="solve")

    state = orchestrator.start("build and solve")

    assert calls[-1] == "solve"
    assert "result" not in calls
    assert state.status == WorkflowStatus.RUNNING
    assert state.current_stage == WorkflowStage.REVIEW
    assert state.execution_result is not None
    assert state.execution_result.error_type == "RuntimeError"
    assert state.execution_result.error_message == "singular matrix"


def test_orchestrator_returns_architect_failure_to_user_input(empty_project, valid_plan) -> None:
    orchestrator, calls = _orchestrator(empty_project, valid_plan, fail_stage="architect")

    state = orchestrator.start("ambiguous request")

    assert calls == ["architect"]
    assert state.status == WorkflowStatus.WAITING_USER_INPUT
    assert state.current_stage == WorkflowStage.ARCHITECT
    assert state.execution_result is not None
    assert state.execution_result.stage == "ARCHITECT"


def test_reviewer_failure_path_stops_for_human_approval(empty_project, valid_plan) -> None:
    calls: list[str] = []
    review = ReviewResult(
        has_problem=True,
        diagnosis="The model lacks a y restraint.",
        evidence=("SOLVE reported singular matrix.",),
        proposals=(
            RepairProposal(
                title="Add y restraint",
                reason="Remove Ty rigid motion.",
                changes={
                    "operation": "add_point_constraint",
                    "target": {"selector": "bottom_left"},
                    "ux": None,
                    "uy": 0.0,
                },
            ),
        ),
    )
    reviewer = FakeReviewer(review, calls)
    orchestrator, workflow_calls = _orchestrator(
        empty_project,
        valid_plan,
        fail_stage="solve",
        reviewer=reviewer,
    )
    reviewer.calls = workflow_calls

    state = orchestrator.start("build and solve")

    assert workflow_calls[-2:] == ["solve", "review"]
    assert state.current_stage == WorkflowStage.APPROVAL
    assert state.status == WorkflowStatus.WAITING_APPROVAL
    assert state.waiting_for_approval is True
    assert state.review_result is review


def test_reject_preserves_plan_project_execution_and_review_context(
    empty_project,
    valid_plan,
) -> None:
    review = ReviewResult(
        has_problem=True,
        diagnosis="Singular model.",
        evidence=("Solver failed.",),
        proposals=(
            RepairProposal(
                title="Add restraint",
                reason="Stabilize model.",
                changes={
                    "operation": "add_point_constraint",
                    "target": {"selector": "bottom_left"},
                    "ux": None,
                    "uy": 0.0,
                },
            ),
        ),
    )
    orchestrator, calls = _orchestrator(empty_project, valid_plan, fail_stage="solve")
    orchestrator.reviewer_agent = FakeReviewer(review, calls)
    state = orchestrator.start("build")
    project_before = state.project.to_dict()
    plan_before = state.simulation_plan
    execution_before = state.execution_result
    review_before = state.review_result

    rejected = orchestrator.handle_approval(False)

    assert rejected.status == WorkflowStatus.WAITING_USER_INPUT
    assert rejected.current_stage == WorkflowStage.ARCHITECT
    assert rejected.project.to_dict() == project_before
    assert rejected.simulation_plan is plan_before
    assert rejected.execution_result is execution_before
    assert rejected.review_result is review_before


def test_confirm_applies_repair_without_reinvoking_architect_and_obeys_retry_limit(
    empty_project,
    valid_plan,
) -> None:
    review = ReviewResult(
        has_problem=True,
        diagnosis="Singular model.",
        evidence=("No point y restraint exists.",),
        proposals=(
            RepairProposal(
                title="Add restraint",
                reason="Remove Ty rigid motion.",
                changes={
                    "operation": "add_point_constraint",
                    "target": {"selector": "bottom_left"},
                    "ux": None,
                    "uy": 0.0,
                },
            ),
        ),
    )
    orchestrator, calls = _orchestrator(
        empty_project,
        valid_plan,
        fail_stage="solve",
        max_retries=1,
    )
    orchestrator.reviewer_agent = FakeReviewer(review, calls)
    orchestrator.start("build")

    retried = orchestrator.handle_approval(True, 0)

    assert retried.simulation_plan is not None
    assert retried.simulation_plan.version == valid_plan.version + 1
    assert retried.retry_count == 1
    assert calls.count("architect") == 1
    assert retried.status == WorkflowStatus.WAITING_APPROVAL

    exhausted_version = retried.simulation_plan.version
    exhausted = orchestrator.handle_approval(True, 0)

    assert exhausted.status == WorkflowStatus.FAILED
    assert exhausted.retry_count == 1
    assert exhausted.simulation_plan.version == exhausted_version


def test_retry_cannot_bypass_human_approval(empty_project, valid_plan) -> None:
    orchestrator, _calls = _orchestrator(empty_project, valid_plan)
    orchestrator.state.simulation_plan = valid_plan

    with pytest.raises(ValueError, match="Human Approval"):
        orchestrator.retry()


def test_manual_revision_resets_stale_mesh_diagnostics_and_full_retry_budget(
    empty_project,
    valid_plan,
) -> None:
    from agent.simulation_plan import SimulationPlan

    calls: list[str] = []
    revised_data = valid_plan.to_dict()
    revised_data["version"] = 2
    revised_plan = SimulationPlan.from_dict(revised_data)
    review = ReviewResult(
        has_problem=True,
        diagnosis="Execution requires a reviewed repair.",
        evidence=("The current execution stage failed.",),
        proposals=(
            RepairProposal(
                title="Add restraint",
                reason="Provide a deterministic retry proposal.",
                changes={
                    "operation": "add_point_constraint",
                    "target": {"selector": "bottom_left"},
                    "ux": None,
                    "uy": 0.0,
                },
            ),
        ),
    )

    class ToggleMaterial(FakeSpecialist):
        should_fail = False

        def apply(self, plan, project):
            self.calls.append(self.label)
            if self.should_fail:
                raise ValueError("revised material failed before mesh")
            return True

    class CapturingReviewer(FakeReviewer):
        def __init__(self, result, review_calls):
            super().__init__(result, review_calls)
            self.diagnostics = []

        def review(self, plan, project, execution_result):
            self.diagnostics.append(execution_result.solve_result)
            return super().review(plan, project, execution_result)

    add_rectangle_part(empty_project, "fake_geometry", 1.0, 1.0)
    material = ToggleMaterial("material", calls)
    reviewer = CapturingReviewer(review, calls)

    def mesh_generator(_geometry, **_kwargs):
        calls.append("mesh")
        return SimpleNamespace(nodes=[1, 2, 3, 4], elements=[1, 2])

    def compiler(**_kwargs):
        calls.append("compile")
        return SimpleNamespace(fem_model=object(), warnings=[])

    def solver(_model):
        calls.append("solve")
        raise RuntimeError("singular matrix")

    orchestrator = WorkflowOrchestrator(
        project=empty_project,
        architect_agent=FakeArchitect(
            valid_plan,
            calls,
            revised_plan=revised_plan,
        ),
        geometry_agent=FakeSpecialist("geometry", calls),
        material_agent=material,
        bc_load_agent=FakeSpecialist("bc_load", calls),
        reviewer_agent=reviewer,
        mesh_generator=mesh_generator,
        compiler=compiler,
        solver=solver,
        result_builder=lambda _solution, _result: {},
        max_retries=2,
    )

    first_cycle = orchestrator.start("build")
    assert first_cycle.status == WorkflowStatus.WAITING_APPROVAL
    assert reviewer.diagnostics[-1]["mesh"] == {
        "exists": True,
        "nodeCount": 4,
        "elementCount": 2,
    }
    first_cycle.retry_count = 1
    first_cycle.result_data = {"stale": True}
    orchestrator.handle_approval(False)
    material.should_fail = True

    revised_cycle = orchestrator.start("revise the model")

    assert revised_cycle.status == WorkflowStatus.WAITING_APPROVAL
    assert revised_cycle.execution_result is not None
    assert revised_cycle.execution_result.stage == "MATERIAL"
    assert revised_cycle.current_mesh is None
    assert revised_cycle.result_data is None
    assert revised_cycle.retry_count == 0
    assert reviewer.diagnostics[-1]["mesh"] == {
        "exists": False,
        "nodeCount": 0,
        "elementCount": 0,
    }

    assert orchestrator.handle_approval(True, 0).retry_count == 1
    assert orchestrator.state.status == WorkflowStatus.WAITING_APPROVAL
    assert orchestrator.handle_approval(True, 0).retry_count == 2
    assert orchestrator.state.status == WorkflowStatus.WAITING_APPROVAL
    exhausted = orchestrator.handle_approval(True, 0)
    assert exhausted.status == WorkflowStatus.FAILED
    assert exhausted.retry_count == 2

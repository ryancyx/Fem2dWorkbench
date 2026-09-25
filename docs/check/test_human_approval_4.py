from __future__ import annotations

from types import SimpleNamespace

from agent.bc_load_agent import BCLoadAgent
from agent.geometry_agent import GeometryAgent
from agent.material_agent import MaterialAgent
from agent.reviewer_agent import ReviewerAgent
from agent.simulation_plan import SimulationPlan
from agent.workflow_orchestrator import WorkflowOrchestrator
from agent.workflow_state import WorkflowStage, WorkflowStatus
from core.engineering.boundary_condition_definition import BoundaryConditionDefinition


class _Architect:
    def __init__(self, plan, calls: list[str], revised_plan=None, *, fail_revise=False) -> None:
        self.plan = plan
        self.calls = calls
        self.revised_plan = revised_plan or plan
        self.fail_revise = fail_revise

    def create_plan(self, _text, _project):
        self.calls.append("architect")
        return self.plan

    def revise_plan(self, _text, _current_plan, _project):
        self.calls.append("architect_revise")
        if self.fail_revise:
            raise ValueError("revision failed")
        return self.revised_plan


class _TracingGeometry:
    def __init__(self, delegate, calls: list[str]) -> None:
        self.delegate = delegate
        self.calls = calls

    def create(self, plan, project):
        self.calls.append("geometry")
        return self.delegate.create(plan, project)


class _TracingMaterial:
    def __init__(self, delegate, calls: list[str]) -> None:
        self.delegate = delegate
        self.calls = calls

    def apply(self, plan, project):
        self.calls.append("material")
        return self.delegate.apply(plan, project)


class _TracingBCLoad:
    def __init__(self, delegate, calls: list[str]) -> None:
        self.delegate = delegate
        self.calls = calls

    def apply(self, plan, project):
        self.calls.append("bc_load")
        return self.delegate.apply(plan, project)

    def clear_managed_definitions(self, project):
        self.calls.append("clear_managed_bc_load")
        return self.delegate.clear_managed_definitions(project)


def test_confirmed_geometry_repair_clears_stale_agent_targets_and_reexecutes_full_plan(
    empty_project,
    valid_plan,
    fake_llm,
) -> None:
    from conftest import FakeLLMClient

    calls: list[str] = []
    reviewer_response = {
        "hasProblem": True,
        "diagnosis": "The geometry should be replaced before retrying the failed solve.",
        "evidence": [
            "The current plan uses a rectangle.",
            "The SOLVE stage returned SingularMatrix.",
        ],
        "proposals": [
            {
                "title": "Replace the rectangle with a circle",
                "reason": "Apply the user-approved geometry correction.",
                "changes": {
                    "operation": "replace_geometry",
                    "geometry": {
                        "type": "circle",
                        "centerX": 0.0,
                        "centerY": 0.0,
                        "radius": 25.0,
                    },
                },
            }
        ],
    }
    solve_attempts = 0

    def mesh_generator(_geometry, **_kwargs):
        calls.append("mesh")
        return SimpleNamespace(nodes=[], elements=[])

    def compiler(*, project, mesh, step_id):
        calls.append("compile")
        assert project is empty_project
        assert mesh is not None
        assert step_id == "step_static"
        return SimpleNamespace(fem_model=object(), warnings=[])

    def solver(_model):
        nonlocal solve_attempts
        calls.append("solve")
        solve_attempts += 1
        if solve_attempts == 1:
            raise RuntimeError("SingularMatrix")
        return object()

    orchestrator = WorkflowOrchestrator(
        project=empty_project,
        architect_agent=_Architect(valid_plan, calls),
        geometry_agent=_TracingGeometry(GeometryAgent(fake_llm), calls),
        material_agent=_TracingMaterial(MaterialAgent(fake_llm), calls),
        bc_load_agent=_TracingBCLoad(BCLoadAgent(fake_llm), calls),
        reviewer_agent=ReviewerAgent(FakeLLMClient(reviewer_response)),
        mesh_generator=mesh_generator,
        compiler=compiler,
        solver=solver,
        result_builder=lambda _solution, result: {"requestedResult": result},
    )

    failed = orchestrator.start("build a model")

    assert failed.status == WorkflowStatus.WAITING_APPROVAL
    old_target_ids = {
        row.target_id for row in empty_project.boundary_conditions + empty_project.loads
    }
    retry_start = len(calls)

    completed = orchestrator.handle_approval(True, 0)

    assert completed.status == WorkflowStatus.COMPLETED
    assert completed.simulation_plan is not None
    assert completed.simulation_plan.version == valid_plan.version + 1
    assert completed.simulation_plan.geometry["type"] == "circle"
    assert completed.retry_count == 1
    assert calls[retry_start:] == [
        "clear_managed_bc_load",
        "geometry",
        "material",
        "bc_load",
        "mesh",
        "compile",
        "solve",
    ]
    assert old_target_ids.isdisjoint(
        {row.target_id for row in empty_project.boundary_conditions + empty_project.loads}
    )
    assert set(empty_project.metadata["agent_boundary_condition_ids"]) == {
        row.id for row in empty_project.boundary_conditions
    }
    assert set(empty_project.metadata["agent_load_ids"]) == {
        row.id for row in empty_project.loads
    }
    empty_project.validate_references()


def test_rejected_geometry_revision_clears_only_managed_targets_and_reexecutes(
    empty_project,
    valid_plan,
    fake_llm,
) -> None:
    from conftest import FakeLLMClient

    circle_data = valid_plan.to_dict()
    circle_data["version"] = 2
    circle_data["geometry"] = {
        "type": "circle",
        "centerX": 0.0,
        "centerY": 0.0,
        "radius": 25.0,
    }
    circle_plan = SimulationPlan.from_dict(circle_data)
    calls: list[str] = []
    reviewer_response = {
        "hasProblem": True,
        "diagnosis": "The failed model requires user review.",
        "evidence": ["The SOLVE stage failed."],
        "proposals": [
            {
                "title": "Reduce mesh size",
                "reason": "Provide one reviewable repair option.",
                "changes": {"operation": "set_mesh_size", "meshSize": 2.5},
            }
        ],
    }
    solve_attempts = 0
    empty_project.add_boundary_condition(
        BoundaryConditionDefinition(
            id="user_bc",
            name="user point restraint",
            step_id=empty_project.analysis_steps[0].id,
            target_type="geometry_point",
            target_id="p1",
            ux_fixed=True,
            uy_fixed=True,
        )
    )

    def mesh_generator(_geometry, **_kwargs):
        calls.append("mesh")
        return SimpleNamespace(nodes=[], elements=[])

    def compiler(**_kwargs):
        calls.append("compile")
        return SimpleNamespace(fem_model=object(), warnings=[])

    def solver(_model):
        nonlocal solve_attempts
        calls.append("solve")
        solve_attempts += 1
        if solve_attempts == 1:
            raise RuntimeError("SingularMatrix")
        return object()

    orchestrator = WorkflowOrchestrator(
        project=empty_project,
        architect_agent=_Architect(valid_plan, calls, circle_plan),
        geometry_agent=_TracingGeometry(GeometryAgent(fake_llm), calls),
        material_agent=_TracingMaterial(MaterialAgent(fake_llm), calls),
        bc_load_agent=_TracingBCLoad(BCLoadAgent(fake_llm), calls),
        reviewer_agent=ReviewerAgent(FakeLLMClient(reviewer_response)),
        mesh_generator=mesh_generator,
        compiler=compiler,
        solver=solver,
        result_builder=lambda _solution, result: {"requestedResult": result},
    )

    failed = orchestrator.start("build rectangle")
    assert failed.status == WorkflowStatus.WAITING_APPROVAL
    old_managed_targets = {
        row.target_id
        for row in empty_project.boundary_conditions
        if row.id in set(empty_project.metadata["agent_boundary_condition_ids"])
    } | {
        row.target_id
        for row in empty_project.loads
        if row.id in set(empty_project.metadata["agent_load_ids"])
    }
    assert orchestrator.handle_approval(False).status == WorkflowStatus.WAITING_USER_INPUT
    revise_start = len(calls)

    completed = orchestrator.start("replace it with a circle")

    assert completed.status == WorkflowStatus.COMPLETED
    assert completed.simulation_plan == circle_plan
    assert completed.retry_count == 0
    assert calls[revise_start:] == [
        "architect_revise",
        "clear_managed_bc_load",
        "geometry",
        "material",
        "bc_load",
        "mesh",
        "compile",
        "solve",
    ]
    assert old_managed_targets.isdisjoint(
        {
            row.target_id
            for row in empty_project.boundary_conditions + empty_project.loads
            if row.id != "user_bc"
        }
    )
    assert empty_project.get_boundary_condition_by_id("user_bc") is not None
    empty_project.validate_references()


def test_failed_architect_revision_does_not_clear_managed_definitions(
    empty_project,
    valid_plan,
    fake_llm,
) -> None:
    calls: list[str] = []
    GeometryAgent(fake_llm).create(valid_plan, empty_project)
    BCLoadAgent(fake_llm).apply(valid_plan, empty_project)
    before_boundary_conditions = list(empty_project.boundary_conditions)
    before_loads = list(empty_project.loads)
    before_metadata = dict(empty_project.metadata)
    orchestrator = WorkflowOrchestrator(
        project=empty_project,
        architect_agent=_Architect(valid_plan, calls, fail_revise=True),
        geometry_agent=_TracingGeometry(GeometryAgent(fake_llm), calls),
        material_agent=_TracingMaterial(MaterialAgent(fake_llm), calls),
        bc_load_agent=_TracingBCLoad(BCLoadAgent(fake_llm), calls),
    )
    orchestrator.state.simulation_plan = valid_plan
    orchestrator.state.current_stage = WorkflowStage.ARCHITECT
    orchestrator.state.status = WorkflowStatus.WAITING_USER_INPUT

    state = orchestrator.start("change the geometry")

    assert state.status == WorkflowStatus.WAITING_USER_INPUT
    assert state.execution_result is not None
    assert state.execution_result.stage == "ARCHITECT"
    assert "clear_managed_bc_load" not in calls
    assert empty_project.boundary_conditions == before_boundary_conditions
    assert empty_project.loads == before_loads
    assert empty_project.metadata == before_metadata
